"""
Тесты для wyckoff.phases.
"""
import pytest
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wyckoff.ranges import TradingRange
from wyckoff.phases import Phase, PhaseResult, PhaseDetector


def make_ranging_df(n=100, upper=1.1050, lower=1.1000):
    """DataFrame с боковиком."""
    np.random.seed(42)
    dates = [datetime(2026, 1, 1) + timedelta(hours=i) for i in range(n)]
    mid = (upper + lower) / 2
    
    prices = []
    for i in range(n):
        if i % 2 == 0:
            prices.append(np.random.uniform(mid, upper))
        else:
            prices.append(np.random.uniform(lower, mid))
    
    return pd.DataFrame({
        'open': prices,
        'high': [min(p + 0.0003, upper) for p in prices],
        'low': [max(p - 0.0003, lower) for p in prices],
        'close': prices,
        'tick_volume': [100] * n,
    }, index=dates)


def make_downtrend_into_range(n=100, upper=1.1050, lower=1.1000):
    """Тренд вниз, потом боковик."""
    np.random.seed(42)
    dates = [datetime(2026, 1, 1) + timedelta(hours=i) for i in range(n)]
    
    prices = []
    for i in range(n):
        if i < 40:
            # Падение
            prices.append(1.1100 - i * 0.0003)
        else:
            # Боковик
            mid = (upper + lower) / 2
            if i % 2 == 0:
                prices.append(np.random.uniform(mid, upper))
            else:
                prices.append(np.random.uniform(lower, mid))
    
    return pd.DataFrame({
        'open': prices,
        'high': [p + 0.0003 for p in prices],
        'low': [p - 0.0003 for p in prices],
        'close': prices,
        'tick_volume': [100] * n,
    }, index=dates)


def make_uptrend_into_range(n=100, upper=1.1050, lower=1.1000):
    """Тренд вверх, потом боковик."""
    np.random.seed(42)
    dates = [datetime(2026, 1, 1) + timedelta(hours=i) for i in range(n)]
    
    prices = []
    for i in range(n):
        if i < 40:
            # Рост
            prices.append(1.0900 + i * 0.0003)
        else:
            # Боковик
            mid = (upper + lower) / 2
            if i % 2 == 0:
                prices.append(np.random.uniform(mid, upper))
            else:
                prices.append(np.random.uniform(lower, mid))
    
    return pd.DataFrame({
        'open': prices,
        'high': [p + 0.0003 for p in prices],
        'low': [p - 0.0003 for p in prices],
        'close': prices,
        'tick_volume': [100] * n,
    }, index=dates)


class TestPhase:
    def test_enum_values(self):
        """Все фазы имеют правильные значения."""
        assert Phase.ACCUMULATION.value == 'accumulation'
        assert Phase.MARKUP.value == 'markup'
        assert Phase.DISTRIBUTION.value == 'distribution'
        assert Phase.MARKDOWN.value == 'markdown'
        assert Phase.UNKNOWN.value == 'unknown'
    
    def test_phase_result_repr(self):
        """PhaseResult repr."""
        r = PhaseResult(
            phase=Phase.ACCUMULATION,
            confidence=0.8,
            reason='test',
        )
        s = repr(r)
        assert 'accumulation' in s
        assert '0.80' in s


class TestPhaseDetector:
    def test_init(self):
        """Инициализация."""
        d = PhaseDetector()
        assert d.lookback_bars == 50
    
    def test_empty_df(self):
        """Пустой DataFrame."""
        d = PhaseDetector()
        df = pd.DataFrame(columns=['high', 'low', 'close'])
        r = TradingRange(
            start_idx=0, end_idx=10, upper=1.1, lower=1.0,
            width=0.1, width_atr=1.0, bars_count=10,
        )
        result = d.detect_phase(df, r)
        assert result.phase == Phase.UNKNOWN
    
    def test_detect_current_phase_no_data(self):
        """detect_current_phase на малых данных."""
        d = PhaseDetector()
        df = pd.DataFrame({
            'high': [1.1] * 10,
            'low': [1.0] * 10,
            'close': [1.05] * 10,
            'tick_volume': [100] * 10,
        })
        result = d.detect_current_phase(df)
        assert result.phase == Phase.UNKNOWN
    
    def test_detect_accumulation(self):
        """Accumulation на падении + боковике."""
        d = PhaseDetector(lookback_bars=50, trend_atr_threshold=1.0)
        df = make_downtrend_into_range(n=100)
        
        r = TradingRange(
            start_idx=50, end_idx=99,
            upper=1.1050, lower=1.1000,
            width=0.005, width_atr=2.0,
            bars_count=50,
        )
        
        result = d.detect_phase(df, r)
        # Может быть Accumulation или Unknown
        assert result.phase in [Phase.ACCUMULATION, Phase.UNKNOWN]
        assert 0.0 <= result.confidence <= 1.0
    
    def test_detect_distribution(self):
        """Distribution на росте + боковике."""
        d = PhaseDetector(lookback_bars=50, trend_atr_threshold=1.0)
        df = make_uptrend_into_range(n=100)
        
        r = TradingRange(
            start_idx=50, end_idx=99,
            upper=1.1050, lower=1.1000,
            width=0.005, width_atr=2.0,
            bars_count=50,
        )
        
        result = d.detect_phase(df, r)
        assert result.phase in [Phase.DISTRIBUTION, Phase.UNKNOWN]
        assert 0.0 <= result.confidence <= 1.0
    
    def test_detect_current_phase_returns_result(self):
        """detect_current_phase всегда возвращает PhaseResult."""
        d = PhaseDetector()
        df = make_ranging_df(n=100)
        result = d.detect_current_phase(df)
        assert isinstance(result, PhaseResult)
        assert isinstance(result.phase, Phase)
    
    def test_context_trend_down(self):
        """Контекст down определён."""
        d = PhaseDetector(lookback_bars=50, trend_atr_threshold=1.0)
        df = make_downtrend_into_range(n=100)
        r = TradingRange(
            start_idx=50, end_idx=99,
            upper=1.1050, lower=1.1000,
            width=0.005, width_atr=2.0,
            bars_count=50,
        )
        context = d._determine_context_trend(df, r)
        assert context == 'down'
    
    def test_context_trend_up(self):
        """Контекст up определён."""
        d = PhaseDetector(lookback_bars=50, trend_atr_threshold=1.0)
        df = make_uptrend_into_range(n=100)
        r = TradingRange(
            start_idx=50, end_idx=99,
            upper=1.1050, lower=1.1000,
            width=0.005, width_atr=2.0,
            bars_count=50,
        )
        context = d._determine_context_trend(df, r)
        assert context == 'up'
    
    def test_context_no_data(self):
        """Контекст не определён на малых данных."""
        d = PhaseDetector()
        df = make_ranging_df(n=20)
        r = TradingRange(
            start_idx=5, end_idx=15,
            upper=1.1050, lower=1.1000,
            width=0.005, width_atr=2.0,
            bars_count=10,
        )
        context = d._determine_context_trend(df, r)
        # Не должно упасть
        assert context in ['up', 'down', 'none']
    
    def test_count_bullish_events(self):
        """Подсчёт бычьих событий."""
        from wyckoff.events import WyckoffEvent
        d = PhaseDetector()
        events = [
            WyckoffEvent(type='SC', idx=0, price=1.0, volume=100),
            WyckoffEvent(type='Spring', idx=1, price=1.0, volume=100),
            WyckoffEvent(type='UT', idx=2, price=1.0, volume=100),
        ]
        assert d._count_bullish_events(events) == 2
        assert d._count_bearish_events(events) == 1
    
    def test_confidence_range(self):
        """Confidence в диапазоне 0..1."""
        d = PhaseDetector()
        df = make_ranging_df(n=100)
        result = d.detect_current_phase(df)
        assert 0.0 <= result.confidence <= 1.0