"""
Wyckoff Phases - определение фазы рынка.

4 фазы (по книге Хатсона):
1. Accumulation - накопление (после падения)
2. Markup       - метка вверх (тренд вверх)
3. Distribution - распределение (после роста)
4. Markdown     - метка вниз (тренд вниз)

Определение фазы базируется на:
- TradingRange (Этап 1)
- WyckoffEvent (Этап 2)
- Контексте: что было до range (тренд вверх или вниз)
"""
import pandas as pd
import numpy as np
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict

from wyckoff.ranges import TradingRange, TradingRangeDetector
from wyckoff.events import WyckoffEvent, WyckoffEventDetector


class Phase(Enum):
    """Фаза рынка по Вайкоффу."""
    ACCUMULATION = 'accumulation'
    MARKUP = 'markup'
    DISTRIBUTION = 'distribution'
    MARKDOWN = 'markdown'
    UNKNOWN = 'unknown'


@dataclass
class PhaseResult:
    """Результат определения фазы."""
    phase: Phase
    confidence: float
    range_obj: Optional[TradingRange] = None
    events: List[WyckoffEvent] = field(default_factory=list)
    reason: str = ''
    meta: Dict = field(default_factory=dict)
    
    def __repr__(self):
        return (
            f"PhaseResult({self.phase.value} "
            f"conf={self.confidence:.2f} reason='{self.reason}')"
        )


class PhaseDetector:
    """
    Определяет фазу рынка по методу Вайкоффа.
    
    Логика:
    1. Находим Trading Range (Этап 1).
    2. Ищем события в range (Этап 2).
    3. Анализируем контекст (тренд до range).
    4. Голосуем за фазу по совокупности сигналов.
    """
    
    def __init__(
        self,
        lookback_bars: int = 50,
        min_bars_for_context: int = 20,
        trend_atr_threshold: float = 0.5,  # было 2.0 - ослаблено
    ):
        """
        Параметры:
        ----------
        lookback_bars : int
            Сколько баров назад смотреть для контекста.
        min_bars_for_context : int
            Минимум баров для определения контекста.
        trend_atr_threshold : float
            Порог тренда в ATR (для определения направления до range).
        """
        self.lookback_bars = lookback_bars
        self.min_bars_for_context = min_bars_for_context
        self.trend_atr_threshold = trend_atr_threshold
    
    def _compute_atr(self, df: pd.DataFrame) -> pd.Series:
        """ATR."""
        high = df['high']
        low = df['low']
        close = df['close']
        prev_close = close.shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ], axis=1).max(axis=1)
        return tr.rolling(window=14, min_periods=1).mean()
    
    def _determine_context_trend(
        self,
        df: pd.DataFrame,
        r: TradingRange,
    ) -> str:
        """
        Определяет, что было ДО range.
        
        Возвращает:
        - 'up'    — цена приходила сверху вниз (был рост)
        - 'down'  — цена приходила снизу вверх (было падение)
        - 'none'  — нет контекста
        """
        start = max(0, r.start_idx - self.lookback_bars)
        if r.start_idx - start < self.min_bars_for_context:
            return 'none'
        
        sub = df.iloc[start:r.start_idx]
        if len(sub) < self.min_bars_for_context:
            return 'none'
        
        atr = self._compute_atr(df)
        first_close = sub['close'].iloc[0]
        last_close = sub['close'].iloc[-1]
        max_atr = atr.iloc[start:r.start_idx].mean()
        
        if max_atr <= 0:
            return 'none'
        
        delta = last_close - first_close
        delta_atr = delta / max_atr
        
        if delta_atr >= self.trend_atr_threshold:
            return 'up'  # рос → значит, придёт сверху вниз
        elif delta_atr <= -self.trend_atr_threshold:
            return 'down'  # падал → значит, придёт снизу вверх
        else:
            return 'none'
    
    def _count_bullish_events(self, events: List[WyckoffEvent]) -> int:
        """Считает бычьи события."""
        bullish_types = {'SC', 'AR', 'ST', 'Spring', 'Test', 'SOS', 'LPS'}
        return sum(1 for e in events if e.type in bullish_types)
    
    def _count_bearish_events(self, events: List[WyckoffEvent]) -> int:
        """Считает медвежьи события."""
        bearish_types = {'UT', 'UTAD', 'SOW', 'LPSY'}
        return sum(1 for e in events if e.type in bearish_types)
    
    def _detect_accumulation(
        self,
        df: pd.DataFrame,
        r: TradingRange,
        events: List[WyckoffEvent],
        context: str,
    ) -> PhaseResult:
        """Определяет Accumulation (накопление)."""
        confidence = 0.0
        reasons = []
        
        # Контекст: должен быть тренд вниз перед range
        if context == 'down':
            confidence += 0.4
            reasons.append('пришёл из падения')
        elif context == 'none':
            confidence += 0.1
            reasons.append('нейтральный контекст')
        else:
            return PhaseResult(
                phase=Phase.UNKNOWN,
                confidence=0.0,
                reason='контекст не подходит для Accumulation',
            )
        
        # Бычьи события внутри
        bullish = self._count_bullish_events(events)
        if bullish >= 2:
            confidence += 0.3
            reasons.append(f'{bullish} бычьих событий')
        elif bullish >= 1:
            confidence += 0.15
            reasons.append(f'{bullish} бычье событие')
        
        # Медвежьих не должно быть много
        bearish = self._count_bearish_events(events)
        if bearish == 0:
            confidence += 0.2
            reasons.append('нет медвежьих событий')
        elif bearish <= 1:
            confidence += 0.1
            reasons.append(f'{bearish} медвежье событие')
        else:
            confidence -= 0.2
            reasons.append(f'много медвежьих ({bearish})')
        
        # Range не слишком широкий
        if r.width_atr <= 3.0:
            confidence += 0.1
            reasons.append(f'узкий range ({r.width_atr:.1f} ATR)')
        
        confidence = max(0.0, min(1.0, confidence))
        
        if confidence >= 0.4:
            return PhaseResult(
                phase=Phase.ACCUMULATION,
                confidence=confidence,
                range_obj=r,
                events=events,
                reason='; '.join(reasons),
                meta={'bullish': bullish, 'bearish': bearish, 'context': context},
            )
        
        return PhaseResult(phase=Phase.UNKNOWN, confidence=confidence)
    
    def _detect_distribution(
        self,
        df: pd.DataFrame,
        r: TradingRange,
        events: List[WyckoffEvent],
        context: str,
    ) -> PhaseResult:
        """Определяет Distribution (распределение)."""
        confidence = 0.0
        reasons = []
        
        # Контекст: должен быть тренд вверх перед range
        if context == 'up':
            confidence += 0.4
            reasons.append('пришёл из роста')
        elif context == 'none':
            confidence += 0.1
            reasons.append('нейтральный контекст')
        else:
            return PhaseResult(
                phase=Phase.UNKNOWN,
                confidence=0.0,
                reason='контекст не подходит для Distribution',
            )
        
        # Медвежьи события внутри
        bearish = self._count_bearish_events(events)
        if bearish >= 2:
            confidence += 0.3
            reasons.append(f'{bearish} медвежьих событий')
        elif bearish >= 1:
            confidence += 0.15
            reasons.append(f'{bearish} медвежье событие')
        
        # Бычьих не должно быть много
        bullish = self._count_bullish_events(events)
        if bullish == 0:
            confidence += 0.2
            reasons.append('нет бычьих событий')
        elif bullish <= 1:
            confidence += 0.1
            reasons.append(f'{bullish} бычье событие')
        else:
            confidence -= 0.2
            reasons.append(f'много бычьих ({bullish})')
        
        if r.width_atr <= 3.0:
            confidence += 0.1
            reasons.append(f'узкий range ({r.width_atr:.1f} ATR)')
        
        confidence = max(0.0, min(1.0, confidence))
        
        if confidence >= 0.4:
            return PhaseResult(
                phase=Phase.DISTRIBUTION,
                confidence=confidence,
                range_obj=r,
                events=events,
                reason='; '.join(reasons),
                meta={'bullish': bullish, 'bearish': bearish, 'context': context},
            )
        
        return PhaseResult(phase=Phase.UNKNOWN, confidence=confidence)
    
    def _detect_markup(
        self,
        df: pd.DataFrame,
        events: List[WyckoffEvent],
    ) -> PhaseResult:
        """Определяет Markup (рост)."""
        # Ищем SOS или LPS как подтверждение роста
        sos_events = [e for e in events if e.type in ('SOS', 'LPS')]
        
        if not sos_events:
            return PhaseResult(phase=Phase.UNKNOWN, confidence=0.0)
        
        # Проверяем, что цена идёт вверх
        last_event = sos_events[-1]
        if last_event.idx < len(df) - 5:
            # После события был откат — берём последние бары
            recent = df.iloc[last_event.idx:]
        else:
            recent = df.iloc[max(0, len(df) - 20):]
        
        if len(recent) < 3:
            return PhaseResult(phase=Phase.UNKNOWN, confidence=0.0)
        
        first_close = recent['close'].iloc[0]
        last_close = recent['close'].iloc[-1]
        
        if last_close > first_close:
            return PhaseResult(
                phase=Phase.MARKUP,
                confidence=0.7,
                events=sos_events,
                reason='SOS + рост цены',
                meta={'first': first_close, 'last': last_close},
            )
        
        return PhaseResult(phase=Phase.UNKNOWN, confidence=0.0)
    
    def _detect_markdown(
        self,
        df: pd.DataFrame,
        events: List[WyckoffEvent],
    ) -> PhaseResult:
        """Определяет Markdown (падение)."""
        sow_events = [e for e in events if e.type in ('SOW', 'LPSY')]
        
        if not sow_events:
            return PhaseResult(phase=Phase.UNKNOWN, confidence=0.0)
        
        last_event = sow_events[-1]
        if last_event.idx < len(df) - 5:
            recent = df.iloc[last_event.idx:]
        else:
            recent = df.iloc[max(0, len(df) - 20):]
        
        if len(recent) < 3:
            return PhaseResult(phase=Phase.UNKNOWN, confidence=0.0)
        
        first_close = recent['close'].iloc[0]
        last_close = recent['close'].iloc[-1]
        
        if last_close < first_close:
            return PhaseResult(
                phase=Phase.MARKDOWN,
                confidence=0.7,
                events=sow_events,
                reason='SOW + падение цены',
                meta={'first': first_close, 'last': last_close},
            )
        
        return PhaseResult(phase=Phase.UNKNOWN, confidence=0.0)
    
    def detect_phase(
        self,
        df: pd.DataFrame,
        r: TradingRange,
    ) -> PhaseResult:
        """
        Определяет фазу для конкретного TradingRange.
        """
        if df is None or len(df) < 20:
            return PhaseResult(phase=Phase.UNKNOWN, confidence=0.0)
        
        # Ищем события в range
        event_detector = WyckoffEventDetector()
        events = event_detector.detect_all(df, r)
        
        # Определяем контекст (тренд до range)
        context = self._determine_context_trend(df, r)
        
        # Проверяем все фазы
        candidates = []
        
        # Accumulation
        acc = self._detect_accumulation(df, r, events, context)
        if acc.phase != Phase.UNKNOWN:
            candidates.append(acc)
        
        # Distribution
        dist = self._detect_distribution(df, r, events, context)
        if dist.phase != Phase.UNKNOWN:
            candidates.append(dist)
        
        # Markup
        markup = self._detect_markup(df, events)
        if markup.phase != Phase.UNKNOWN:
            candidates.append(markup)
        
        # Markdown
        markdown = self._detect_markdown(df, events)
        if markdown.phase != Phase.UNKNOWN:
            candidates.append(markdown)
        
        # Возвращаем с наибольшей уверенностью
        if not candidates:
            return PhaseResult(
                phase=Phase.UNKNOWN,
                confidence=0.0,
                range_obj=r,
                events=events,
                reason='нет явных сигналов',
            )
        
        candidates.sort(key=lambda x: x.confidence, reverse=True)
        best = candidates[0]
        
        return PhaseResult(
            phase=best.phase,
            confidence=best.confidence,
            range_obj=r,
            events=best.events,
            reason=best.reason,
            meta=best.meta,
        )
    
    def detect_current_phase(
        self,
        df: pd.DataFrame,
        ranges: Optional[List[TradingRange]] = None,
    ) -> PhaseResult:
        """
        Определяет текущую фазу.
        
        Логика:
        1. Если передан список ranges — берём ПОСЛЕДНИЙ.
        2. Если нет — ищем сами.
        3. Определяем фазу для последнего range.
        4. Если range нет — Markup / Markdown по последним событиям.
        """
        if df is None or len(df) < 20:
            return PhaseResult(phase=Phase.UNKNOWN, confidence=0.0)
        
        # Получаем ranges
        if ranges is None:
            range_detector = TradingRangeDetector()
            ranges = range_detector.find_ranges(df)
        
        # Берём ПОСЛЕДНИЙ range
        if ranges:
            last_range = ranges[-1]
            return self.detect_phase(df, last_range)
        
        # Нет ranges — пробуем Markup/Markdown
        event_detector = WyckoffEventDetector()
        temp_range = TradingRange(
            start_idx=max(0, len(df) - 50),
            end_idx=len(df) - 1,
            upper=df['high'].iloc[-50:].max(),
            lower=df['low'].iloc[-50:].min(),
            width=df['high'].iloc[-50:].max() - df['low'].iloc[-50:].min(),
            width_atr=2.0,
            bars_count=50,
        )
        events = event_detector.detect_all(df, temp_range)
        
        markup = self._detect_markup(df, events)
        markdown = self._detect_markdown(df, events)
        
        if markup.phase != Phase.UNKNOWN and markdown.phase != Phase.UNKNOWN:
            return markup if markup.confidence >= markdown.confidence else markdown
        if markup.phase != Phase.UNKNOWN:
            return markup
        if markdown.phase != Phase.UNKNOWN:
            return markdown
        
        return PhaseResult(
            phase=Phase.UNKNOWN,
            confidence=0.0,
            events=events,
            reason='нет сигналов',
        )