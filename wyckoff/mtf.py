"""
Wyckoff MTF - мультитаймфреймовый анализ.

Логика (по книге Хатсона, стр. 13):
- Старший ТФ (D1) определяет глобальную фазу.
- Средний ТФ (H4) подтверждает.
- Младший ТФ (H1) даёт точку входа.

Согласованность ТФ = сильный сигнал.
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from wyckoff.detector import WyckoffDetector, WyckoffAnalysis
from wyckoff.phases import Phase


# Порядок ТФ (от младшего к старшему)
TIMEFRAME_ORDER = ['M15', 'M30', 'H1', 'H4', 'D1', 'W1']


@dataclass
class MTFResult:
    """Результат MTF-анализа."""
    analyses: Dict[str, WyckoffAnalysis] = field(default_factory=dict)
    summary: str = ''
    signal: str = 'WAIT'         # 'BUY', 'SELL', 'WAIT'
    confidence: float = 0.0      # 0..1
    alignment: str = 'mixed'     # 'bullish', 'bearish', 'mixed', 'neutral'
    meta: Dict = field(default_factory=dict)
    
    def __repr__(self):
        return (
            f"MTFResult(signal={self.signal}, "
            f"conf={self.confidence:.2f}, "
            f"alignment={self.alignment}, "
            f"timeframes={list(self.analyses.keys())})"
        )


class WyckoffMTFAnalyzer:
    """
    Мультитаймфреймовый анализатор Wyckoff.
    """
    
    def __init__(
        self,
        detector: Optional[WyckoffDetector] = None,
        timeframes: Optional[List[str]] = None,
    ):
        """
        Параметры:
        ----------
        detector : WyckoffDetector, optional
            Готовый детектор. Если None — создаётся с дефолтами.
        timeframes : List[str], optional
            Список ТФ (например, ['H1', 'H4', 'D1']).
            Если None — авто из переданных данных.
        """
        self.detector = detector or WyckoffDetector()
        self.timeframes = timeframes
    
    def _sort_timeframes(self, tfs: List[str]) -> List[str]:
        """Сортирует ТФ от младшего к старшему."""
        def key(tf):
            return TIMEFRAME_ORDER.index(tf) if tf in TIMEFRAME_ORDER else 999
        return sorted(tfs, key=key)
    
    def _analyze_bullish_score(
        self,
        analysis: WyckoffAnalysis,
    ) -> float:
        """
        Оценка бычьей силы анализа (0..1).
        """
        if analysis is None:
            return 0.0
        
        score = 0.0
        
        # Фаза
        if analysis.current_phase:
            phase = analysis.current_phase.phase
            conf = analysis.current_phase.confidence
            if phase == Phase.ACCUMULATION:
                score += 0.4 * conf
            elif phase == Phase.MARKUP:
                score += 0.5 * conf
        
        # Бычьи события
        bullish = analysis.get_bullish_events()
        if bullish:
            # Spring, SOS, LPS — самые сильные
            strong = [e for e in bullish if e.type in ('Spring', 'SOS', 'LPS', 'SC')]
            score += min(0.4, len(strong) * 0.15)
            # Слабые
            score += min(0.1, len(bullish) * 0.03)
        
        # RS
        if analysis.rs:
            if analysis.rs.rs_trend == 'rising':
                score += 0.2
            if analysis.rs.rs_rank >= 70:
                score += 0.1
        
        # Пробои линий вверх
        breaks_up = [
            b for b in analysis.trendline_breaks
            if b.direction == 'up'
        ]
        if breaks_up:
            score += min(0.2, len(breaks_up) * 0.1)
        
        return min(1.0, score)
    
    def _analyze_bearish_score(
        self,
        analysis: WyckoffAnalysis,
    ) -> float:
        """
        Оценка медвежьей силы анализа (0..1).
        """
        if analysis is None:
            return 0.0
        
        score = 0.0
        
        # Фаза
        if analysis.current_phase:
            phase = analysis.current_phase.phase
            conf = analysis.current_phase.confidence
            if phase == Phase.DISTRIBUTION:
                score += 0.4 * conf
            elif phase == Phase.MARKDOWN:
                score += 0.5 * conf
        
        # Медвежьи события
        bearish = analysis.get_bearish_events()
        if bearish:
            strong = [e for e in bearish if e.type in ('UT', 'UTAD', 'SOW', 'LPSY')]
            score += min(0.4, len(strong) * 0.15)
            score += min(0.1, len(bearish) * 0.03)
        
        # RS
        if analysis.rs:
            if analysis.rs.rs_trend == 'falling':
                score += 0.2
            if analysis.rs.rs_rank <= 30:
                score += 0.1
        
        # Пробои линий вниз
        breaks_down = [
            b for b in analysis.trendline_breaks
            if b.direction == 'down'
        ]
        if breaks_down:
            score += min(0.2, len(breaks_down) * 0.1)
        
        return min(1.0, score)
    
    def analyze_all(
        self,
        data: Dict[str, pd.DataFrame],
        benchmark_data: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> MTFResult:
        """
        Анализ всех ТФ.
        
        Параметры:
        ----------
        data : Dict[str, pd.DataFrame]
            {'H1': df_h1, 'H4': df_h4, 'D1': df_d1}.
        benchmark_data : Dict[str, pd.DataFrame], optional
            То же для эталона (для RS).
        
        Возвращает:
        -----------
        MTFResult
        """
        result = MTFResult()
        
        if not data:
            result.summary = 'No data'
            return result
        
        # Сортируем ТФ
        sorted_tfs = self._sort_timeframes(list(data.keys()))
        
        # Анализируем каждый ТФ
        for tf in sorted_tfs:
            df = data.get(tf)
            if df is None or len(df) < 20:
                continue
            
            benchmark_df = None
            if benchmark_data and tf in benchmark_data:
                benchmark_df = benchmark_data[tf]
            
            try:
                analysis = self.detector.detect_all(df, benchmark_df=benchmark_df)
                result.analyses[tf] = analysis
            except Exception as e:
                print(f"[WARN] MTF {tf}: {e}")
        
        if not result.analyses:
            result.summary = 'No valid analyses'
            return result
        
        # Считаем бычьи и медвежьи оценки
        bullish_scores = {}
        bearish_scores = {}
        for tf, analysis in result.analyses.items():
            bullish_scores[tf] = self._analyze_bullish_score(analysis)
            bearish_scores[tf] = self._analyze_bearish_score(analysis)
        
        # Итоговый сигнал
        # Взвешенно: старшие ТФ важнее
        total_bullish = 0.0
        total_bearish = 0.0
        total_weight = 0.0
        
        for tf in sorted_tfs:
            if tf not in result.analyses:
                continue
            # Вес: младший = 1, старший = 2
            weight = 1.0 + TIMEFRAME_ORDER.index(tf) / len(TIMEFRAME_ORDER)
            total_weight += weight
            total_bullish += bullish_scores[tf] * weight
            total_bearish += bearish_scores[tf] * weight
        
        if total_weight > 0:
            total_bullish /= total_weight
            total_bearish /= total_weight
        
        # Согласованность
        bullish_tfs = [tf for tf, s in bullish_scores.items() if s >= 0.4]
        bearish_tfs = [tf for tf, s in bearish_scores.items() if s >= 0.4]
        
        if len(bullish_tfs) == len(result.analyses) and total_bullish > 0.4:
            result.alignment = 'bullish'
            result.signal = 'BUY'
            result.confidence = total_bullish
        elif len(bearish_tfs) == len(result.analyses) and total_bearish > 0.4:
            result.alignment = 'bearish'
            result.signal = 'SELL'
            result.confidence = total_bearish
        elif total_bullish > 0.5 and total_bullish > total_bearish * 1.5:
            result.alignment = 'bullish'
            result.signal = 'BUY'
            result.confidence = total_bullish * 0.7
        elif total_bearish > 0.5 and total_bearish > total_bullish * 1.5:
            result.alignment = 'bearish'
            result.signal = 'SELL'
            result.confidence = total_bearish * 0.7
        else:
            result.alignment = 'mixed'
            result.signal = 'WAIT'
            result.confidence = 0.0
        
        result.meta = {
            'bullish_scores': {k: round(v, 2) for k, v in bullish_scores.items()},
            'bearish_scores': {k: round(v, 2) for k, v in bearish_scores.items()},
            'total_bullish': round(total_bullish, 2),
            'total_bearish': round(total_bearish, 2),
            'bullish_tfs': bullish_tfs,
            'bearish_tfs': bearish_tfs,
        }
        
        # Summary
        result.summary = self._build_summary(result)
        
        return result
    
    def _build_summary(self, result: MTFResult) -> str:
        """Строит текстовую сводку."""
        parts = []
        
        # Фазы по ТФ
        for tf in self._sort_timeframes(list(result.analyses.keys())):
            analysis = result.analyses[tf]
            phase = (
                analysis.current_phase.phase.value
                if analysis.current_phase else 'none'
            )
            parts.append(f"{tf}:{phase}")
        
        summary = ' | '.join(parts)
        
        # Сигнал
        summary += f" → {result.signal}"
        
        if result.confidence > 0:
            summary += f" ({result.confidence:.2f})"
        
        return summary
    
    def get_alignment(self) -> str:
        """Возвращает согласованность (последний результат)."""
        return 'mixed'
    
    def get_phase_by_tf(
        self,
        result: MTFResult,
    ) -> Dict[str, str]:
        """Возвращает фазу по каждому ТФ."""
        phases = {}
        for tf, analysis in result.analyses.items():
            if analysis.current_phase:
                phases[tf] = analysis.current_phase.phase.value
            else:
                phases[tf] = 'unknown'
        return phases
    
    def get_events_by_tf(
        self,
        result: MTFResult,
    ) -> Dict[str, List[str]]:
        """Возвращает события по каждому ТФ."""
        events = {}
        for tf, analysis in result.analyses.items():
            events[tf] = [e.type for e in analysis.events]
        return events