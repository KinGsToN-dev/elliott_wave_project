"""
WyckoffDetector - фасад для всего модуля Wyckoff.

Объединяет:
- TradingRangeDetector   (Этап 1)
- WyckoffEventDetector   (Этап 2)
- PhaseDetector          (Этап 3)
- VolumeAnalyzer         (Этап 4)
- TrendlineDetector      (Этап 5)
- RelativeStrengthAnalyzer (Этап 6)

Использование:
    detector = WyckoffDetector()
    result = detector.detect_all(df)
    print(result.summary)
    
    # Сравнение с benchmark (для RS)
    result = detector.detect_all(df, benchmark_df=index_df)
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Dict

from wyckoff.ranges import TradingRange, TradingRangeDetector
from wyckoff.events import WyckoffEvent, WyckoffEventDetector
from wyckoff.phases import Phase, PhaseResult, PhaseDetector
from wyckoff.volume import VolumeSignal, VolumeAnalyzer
from wyckoff.trendlines import Trendline, TrendlineBreak, TrendlineDetector
from wyckoff.relative_strength import RSResult, RelativeStrengthAnalyzer


@dataclass
class WyckoffAnalysis:
    """Полный результат анализа Wyckoff."""
    # Trading Ranges
    ranges: List[TradingRange] = field(default_factory=list)
    current_range: Optional[TradingRange] = None
    
    # Events
    events: List[WyckoffEvent] = field(default_factory=list)
    
    # Phases
    current_phase: Optional[PhaseResult] = None
    
    # Volume
    volume_signals: List[VolumeSignal] = field(default_factory=list)
    volume_analysis: Dict = field(default_factory=dict)
    
    # Trendlines
    trendlines: List[Trendline] = field(default_factory=list)
    trendline_breaks: List[TrendlineBreak] = field(default_factory=list)
    
    # Relative Strength
    rs: Optional[RSResult] = None
    
    # Summary
    summary: str = ''
    
    def to_dict(self) -> Dict:
        """Конвертирует в словарь для сериализации."""
        return {
            'ranges_count': len(self.ranges),
            'current_range': (
                {
                    'start_idx': self.current_range.start_idx,
                    'end_idx': self.current_range.end_idx,
                    'upper': self.current_range.upper,
                    'lower': self.current_range.lower,
                    'width_atr': self.current_range.width_atr,
                    'bars_count': self.current_range.bars_count,
                } if self.current_range else None
            ),
            'events': [
                {
                    'type': e.type,
                    'idx': e.idx,
                    'price': e.price,
                    'volume': e.volume,
                    'direction': e.direction,
                    'confidence': e.confidence,
                } for e in self.events
            ],
            'phase': (
                {
                    'phase': self.current_phase.phase.value,
                    'confidence': self.current_phase.confidence,
                    'reason': self.current_phase.reason,
                } if self.current_phase else None
            ),
            'volume_signals_count': len(self.volume_signals),
            'trendlines_count': len(self.trendlines),
            'trendline_breaks_count': len(self.trendline_breaks),
            'rs': (
                {
                    'value': self.rs.rs_value,
                    'trend': self.rs.rs_trend,
                    'rank': self.rs.rs_rank,
                    'is_stronger': self.rs.is_stronger,
                } if self.rs else None
            ),
        }
    
    def get_bullish_events(self) -> List[WyckoffEvent]:
        """Все бычьи события."""
        bullish = {'SC', 'AR', 'ST', 'Spring', 'Test', 'SOS', 'LPS'}
        return [e for e in self.events if e.type in bullish]
    
    def get_bearish_events(self) -> List[WyckoffEvent]:
        """Все медвежьи события."""
        bearish = {'UT', 'UTAD', 'SOW', 'LPSY'}
        return [e for e in self.events if e.type in bearish]
    
    def has_phase(self, phase: Phase) -> bool:
        """Проверяет, является ли текущая фаза указанной."""
        if self.current_phase is None:
            return False
        return self.current_phase.phase == phase
    
    def __repr__(self):
        return (
            f"WyckoffAnalysis(ranges={len(self.ranges)}, "
            f"events={len(self.events)}, "
            f"phase={self.current_phase.phase.value if self.current_phase else 'none'}, "
            f"trendlines={len(self.trendlines)})"
        )


class WyckoffDetector:
    """
    Фасад для всего модуля Wyckoff.
    
    Объединяет все детекторы в один вызов.
    """
    
    def __init__(
        self,
        # Range
        range_min_bars: int = 20,
        range_max_width_atr: float = 3.0,
        # Events
        climax_volume_mult: float = 2.0,
        spring_depth_atr: float = 0.5,
        # Phases
        phase_lookback_bars: int = 50,
        phase_trend_atr_threshold: float = 2.0,
        # Volume
        volume_ma_period: int = 20,
        # Trendlines
        zigzag_length: int = 5,
        # RS
        rs_trend_period: int = 20,
        rs_flat_threshold: float = 0.002,
    ):
        """Инициализация со всеми параметрами."""
        self.range_detector = TradingRangeDetector(
            min_bars=range_min_bars,
            max_width_atr=range_max_width_atr,
        )
        self.event_detector = WyckoffEventDetector(
            climax_volume_mult=climax_volume_mult,
            spring_depth_atr=spring_depth_atr,
        )
        self.phase_detector = PhaseDetector(
            lookback_bars=phase_lookback_bars,
            trend_atr_threshold=phase_trend_atr_threshold,
        )
        self.volume_analyzer = VolumeAnalyzer(
            volume_ma_period=volume_ma_period,
        )
        self.trendline_detector = TrendlineDetector(
            zigzag_length=zigzag_length,
        )
        self.rs_analyzer = RelativeStrengthAnalyzer(
            trend_period=rs_trend_period,
            flat_threshold=rs_flat_threshold,
        )
    
    def _build_summary(
        self,
        result: WyckoffAnalysis,
    ) -> str:
        """Строит текстовую сводку."""
        parts = []
        
        # Фаза
        if result.current_phase:
            phase_name = result.current_phase.phase.value.upper()
            conf = result.current_phase.confidence
            parts.append(f"Phase: {phase_name} (conf={conf:.2f})")
        
        # Range
        if result.current_range:
            r = result.current_range
            parts.append(
                f"Range: [{r.lower:.5f}, {r.upper:.5f}] "
                f"({r.bars_count} bars, {r.width_atr:.2f} ATR)"
            )
        
        # События
        if result.events:
            event_types = [e.type for e in result.events]
            parts.append(f"Events: {', '.join(event_types)}")
        
        # RS
        if result.rs:
            parts.append(
                f"RS: {result.rs.rs_trend} "
                f"(rank={result.rs.rs_rank:.0f}%)"
            )
        
        # Trendlines
        if result.trendlines:
            line_types = [t.type.value for t in result.trendlines]
            parts.append(f"Trendlines: {', '.join(line_types)}")
        
        return ' | '.join(parts) if parts else 'No signals'
    
    def detect_all(
        self,
        df: pd.DataFrame,
        benchmark_df: Optional[pd.DataFrame] = None,
    ) -> WyckoffAnalysis:
        """
        Полный анализ Wyckoff.
        
        Параметры:
        ----------
        df : pd.DataFrame
            OHLCV данных.
        benchmark_df : pd.DataFrame, optional
            Эталон для RS (например, индекс). Если None — RS не считается.
        
        Возвращает:
        -----------
        WyckoffAnalysis
        """
        result = WyckoffAnalysis()
        
        if df is None or len(df) < 20:
            result.summary = 'Not enough data'
            return result
        
        # 1. Trading Ranges
        try:
            result.ranges = self.range_detector.find_ranges(df)
            result.current_range = self.range_detector.get_current_range(df)
        except Exception as e:
            print(f"[WARN] Range detection: {e}")
        
        # 2. Events (в текущем range)
               
        if result.ranges:
            try:
                for r in result.ranges:
                    events = self.event_detector.detect_all(df, r)
                    result.events.extend(events)
            except Exception as e:
                print(f"[WARN] Event detection: {e}")
        
        # Дедупликация events по (type, idx)
        seen = set()
        unique_events = []
        for e in result.events:
            key = (e.type, e.idx)
            if key not in seen:
                seen.add(key)
                unique_events.append(e)
        result.events = unique_events
        
        # 3. Phases (используем последний range)
        try:
            result.current_phase = self.phase_detector.detect_current_phase(
                df, ranges=result.ranges
            )
        except Exception as e:
            print(f"[WARN] Phase detection: {e}")
        
        # 4. Volume
        try:
            volume_result = self.volume_analyzer.analyze(
                df, result.current_range
            )
            result.volume_signals = volume_result.get('signals', [])
            result.volume_analysis = {
                k: v for k, v in volume_result.items() if k != 'signals'
            }
        except Exception as e:
            print(f"[WARN] Volume analysis: {e}")
        
        # 5. Trendlines
        try:
            result.trendlines = self.trendline_detector.detect_all(df)
            result.trendline_breaks = self.trendline_detector.detect_all_breaks(
                df, result.trendlines
            )
        except Exception as e:
            print(f"[WARN] Trendlines: {e}")
        
        # 6. Relative Strength
        if benchmark_df is not None:
            try:
                result.rs = self.rs_analyzer.analyze(df, benchmark_df)
            except Exception as e:
                print(f"[WARN] RS: {e}")
        
        # 7. Summary
        result.summary = self._build_summary(result)
        
        return result
    
    def quick_scan(
        self,
        df: pd.DataFrame,
    ) -> Dict:
        """
        Быстрый скан — только ключевые сигналы.
        
        Возвращает компактный словарь для live-режима.
        """
        analysis = self.detect_all(df)
        
        return {
            'phase': (
                analysis.current_phase.phase.value
                if analysis.current_phase else 'unknown'
            ),
            'phase_confidence': (
                analysis.current_phase.confidence
                if analysis.current_phase else 0.0
            ),
            'has_range': analysis.current_range is not None,
            'bullish_events': [e.type for e in analysis.get_bullish_events()],
            'bearish_events': [e.type for e in analysis.get_bearish_events()],
            'volume_signals': [s.type for s in analysis.volume_signals],
            'summary': analysis.summary,
        }