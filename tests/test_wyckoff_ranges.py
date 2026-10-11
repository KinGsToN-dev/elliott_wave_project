"""
Тесты для wyckoff.ranges (Trading Range).
"""
import pytest
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wyckoff.ranges import TradingRange, TradingRangeDetector


def make_trending_df(n=100, direction='up'):
    """DataFrame с трендом."""
    np.random.seed(42)
    dates = [datetime(2026, 1, 1) + timedelta(hours=i) for i in range(n)]
    
    if direction == 'up':
        prices = [1.1000 + i * 0.0005 + np.random.randn() * 0.0005 for i in range(n)]
    else:
        prices = [1.1000 - i * 0.0005 + np.random.randn() * 0.0005 for i in range(n)]
    
    return pd.DataFrame({
        'open': prices,
        'high': [p + 0.0005 for p in prices],
        'low': [p - 0.0005 for p in prices],
        'close': prices,
        'tick_volume': [100] * n,
    }, index=dates)


def make_ranging_df(n=50, upper=1.1050, lower=1.1000):
    """DataFrame с боковиком."""
    np.random.seed(42)
    dates = [datetime(2026, 1, 1) + timedelta(hours=i) for i in range(n)]
    mid = (upper + lower) / 2
    
    prices = []
    for i in range(n):
        # Осцилляция между границами
        if i % 2 == 0:
            prices.append(np.random.uniform(mid, upper))
        else:
            prices.append(np.random.uniform(lower, mid))
    
    return pd.DataFrame({
        'open': prices,
        'high': [max(p + 0.0003, lower) for p in prices],
        'low': [min(p - 0.0003, upper) for p in prices],
        'close': prices,
        'tick_volume': [100] * n,
    }, index=dates)


class TestTradingRangeDetector:
    def test_init(self):
        """Инициализация."""
        detector = TradingRangeDetector()
        assert detector.min_bars == 30      # было 20
        assert detector.max_width_atr == 2.5  # было 3.0
    
    def test_empty_df(self):
        """Пустой DataFrame — пустой список."""
        detector = TradingRangeDetector()
        df = pd.DataFrame(columns=['high', 'low', 'close'])
        result = detector.find_ranges(df)
        assert result == []
    
    def test_too_few_bars(self):
        """Мало баров — пустой список."""
        detector = TradingRangeDetector(min_bars=20)
        df = make_trending_df(n=10)
        result = detector.find_ranges(df)
        assert result == []
    
    def test_missing_columns(self):
        """Нет нужных колонок — ValueError."""
        detector = TradingRangeDetector()
        df = pd.DataFrame({'price': [1, 2, 3]})
        with pytest.raises(ValueError):
            detector.find_ranges(df)
    
    def test_trending_up_no_range(self):
        """Тренд вверх — range не найден."""
        detector = TradingRangeDetector(
            min_bars=20,
            max_width_atr=2.0,
        )
        df = make_trending_df(n=100, direction='up')
        result = detector.find_ranges(df)
        # В тренде range быть не должно
        assert len(result) == 0
    
    def test_trending_down_no_range(self):
        """Тренд вниз — range не найден."""
        detector = TradingRangeDetector(
            min_bars=20,
            max_width_atr=2.0,
        )
        df = make_trending_df(n=100, direction='down')
        result = detector.find_ranges(df)
        assert len(result) == 0
    
    def test_ranging_df_found(self):
        """Боковик найден."""
        detector = TradingRangeDetector(
            min_bars=20,
            max_width_atr=3.0,
        )
        df = make_ranging_df(n=50)
        result = detector.find_ranges(df)
        assert len(result) >= 1
        r = result[0]
        assert r.bars_count >= 20
        assert r.upper > r.lower
        assert r.width_atr > 0
    
    def test_range_touches(self):
        """Касания границ посчитаны."""
        detector = TradingRangeDetector(min_bars=20)
        df = make_ranging_df(n=50)
        result = detector.find_ranges(df)
        
        if len(result) > 0:
            r = result[0]
            # Касания должны быть минимум по одному
            assert r.touches_upper >= 1
            assert r.touches_lower >= 1
    
    def test_get_current_range(self):
        """Текущий range определён."""
        detector = TradingRangeDetector(min_bars=20)
        df = make_ranging_df(n=50)
        r = detector.get_current_range(df)
        # Не факт, что найдётся, но не должно упасть
        assert r is None or isinstance(r, TradingRange)
    
    def test_is_price_in_range(self):
        """Проверка нахождения цены в range."""
        detector = TradingRangeDetector()
        r = TradingRange(
            start_idx=0, end_idx=50,
            upper=1.1050, lower=1.1000,
            width=0.0050, width_atr=2.0,
            bars_count=50,
        )
        assert detector.is_price_in_range(1.1025, r) is True
        assert detector.is_price_in_range(1.1100, r) is False
        assert detector.is_price_in_range(1.0990, r) is False
    
    def test_get_position_in_range(self):
        """Позиция в range."""
        detector = TradingRangeDetector()
        r = TradingRange(
            start_idx=0, end_idx=50,
            upper=1.1100, lower=1.1000,
            width=0.0100, width_atr=2.0,
            bars_count=50,
        )
        # На нижней границе
        assert detector.get_position_in_range(1.1000, r) == 0.0
        # На верхней границе
        assert detector.get_position_in_range(1.1100, r) == 1.0
        # В середине
        assert abs(detector.get_position_in_range(1.1050, r) - 0.5) < 0.01
        # Вне range (clamp)
        assert detector.get_position_in_range(1.1150, r) == 1.0
        assert detector.get_position_in_range(1.0950, r) == 0.0
    
    def test_range_repr(self):
        """repr работает."""
        r = TradingRange(
            start_idx=0, end_idx=50,
            upper=1.1050, lower=1.1000,
            width=0.0050, width_atr=2.0,
            bars_count=50,
            touches_upper=3,
            touches_lower=4,
        )
        s = repr(r)
        assert 'TradingRange' in s
        assert 'bars=50' in s
        assert 'upper' in s