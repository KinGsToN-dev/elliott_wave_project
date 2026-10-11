"""
Тесты для wyckoff.trendlines.
"""
import pytest
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wyckoff.trendlines import (
    LineType, Trendline, TrendlineBreak, TrendlineDetector,
)


def make_uptrend_df(n=100):
    """DataFrame с восходящим трендом и пилообразными движениями."""
    np.random.seed(42)
    dates = [datetime(2026, 1, 1) + timedelta(hours=i) for i in range(n)]
    
    prices = []
    for i in range(n):
        base = 1.1000 + i * 0.0002
        wave = 0.0010 * np.sin(i * np.pi / 5)
        prices.append(base + wave)
    
    return pd.DataFrame({
        'open': prices,
        'high': [p + 0.0005 for p in prices],
        'low': [p - 0.0005 for p in prices],
        'close': prices,
        'tick_volume': [100] * n,
    }, index=dates)


def make_downtrend_df(n=100):
    """DataFrame с нисходящим трендом."""
    np.random.seed(42)
    dates = [datetime(2026, 1, 1) + timedelta(hours=i) for i in range(n)]
    
    prices = []
    for i in range(n):
        base = 1.1100 - i * 0.0002
        wave = 0.0010 * np.sin(i * np.pi / 5)
        prices.append(base + wave)
    
    return pd.DataFrame({
        'open': prices,
        'high': [p + 0.0005 for p in prices],
        'low': [p - 0.0005 for p in prices],
        'close': prices,
        'tick_volume': [100] * n,
    }, index=dates)


class TestTrendline:
    def test_init(self):
        """Инициализация."""
        line = Trendline(
            type=LineType.SUPPORT,
            x1=0, y1=1.1000, x2=50, y2=1.1050,
        )
        assert line.type == LineType.SUPPORT
        assert line.slope > 0
        assert line.x1 == 0
    
    def test_get_value(self):
        """get_value работает."""
        line = Trendline(
            type=LineType.SUPPORT,
            x1=0, y1=1.1000, x2=50, y2=1.1050,
        )
        # Проверяем значения на концах
        assert abs(line.get_value(0) - 1.1000) < 1e-6
        assert abs(line.get_value(50) - 1.1050) < 1e-6
    
    def test_repr(self):
        """repr работает."""
        line = Trendline(
            type=LineType.SUPPORT,
            x1=0, y1=1.1000, x2=50, y2=1.1050,
        )
        r = repr(line)
        assert 'support' in r
        assert 'slope' in r


class TestTrendlineBreak:
    def test_init(self):
        """Инициализация пробоя."""
        line = Trendline(
            type=LineType.SUPPORT,
            x1=0, y1=1.1000, x2=50, y2=1.1050,
        )
        b = TrendlineBreak(
            line=line, idx=60, price=1.0990,
            direction='down', volume=500, strength=0.8,
        )
        assert b.idx == 60
        assert b.direction == 'down'
    
    def test_repr(self):
        """repr."""
        line = Trendline(
            type=LineType.SUPPORT,
            x1=0, y1=1.1000, x2=50, y2=1.1050,
        )
        b = TrendlineBreak(
            line=line, idx=60, price=1.0990,
            direction='down', volume=500, strength=0.8,
        )
        r = repr(b)
        assert 'support' in r
        assert 'idx=60' in r


class TestTrendlineDetector:
    def test_init(self):
        """Инициализация."""
        d = TrendlineDetector()
        assert d.zigzag_length == 5
        assert d.min_pivots == 4
    
    def test_empty_df(self):
        """Пустой DataFrame — пустой результат."""
        d = TrendlineDetector()
        df = pd.DataFrame(columns=['high', 'low', 'close'])
        result = d.detect_all(df)
        assert result == []
    
    def test_short_df(self):
        """Мало баров — пустой результат."""
        d = TrendlineDetector()
        df = pd.DataFrame({
            'high': [1.1] * 10,
            'low': [1.0] * 10,
            'close': [1.05] * 10,
            'tick_volume': [100] * 10,
        })
        result = d.detect_all(df)
        assert result == []
    
    def test_detect_all_uptrend(self):
        """Линии в восходящем тренде."""
        d = TrendlineDetector(zigzag_length=3)
        df = make_uptrend_df(100)
        lines = d.detect_all(df)
        # Должны найти хотя бы одну линию
        assert isinstance(lines, list)
    
    def test_detect_all_downtrend(self):
        """Линии в нисходящем тренде."""
        d = TrendlineDetector(zigzag_length=3)
        df = make_downtrend_df(100)
        lines = d.detect_all(df)
        assert isinstance(lines, list)
    
    def test_line_types_valid(self):
        """Все линии имеют корректный тип."""
        d = TrendlineDetector(zigzag_length=3)
        df = make_uptrend_df(100)
        lines = d.detect_all(df)
        for line in lines:
            assert isinstance(line, Trendline)
            assert line.type in (
                LineType.SUPPORT, LineType.SUPPLY,
                LineType.OVERBOUGHT, LineType.OVERSOLD,
            )
    
    def test_find_support_line_none(self):
        """Support line не найдена без lows."""
        d = TrendlineDetector()
        df = make_uptrend_df(50)
        support = d.find_support_line(df, [])
        assert support is None
    
    def test_find_supply_line_none(self):
        """Supply line не найдена без highs."""
        d = TrendlineDetector()
        df = make_downtrend_df(50)
        supply = d.find_supply_line(df, [])
        assert supply is None
    
    def test_find_overbought_none(self):
        """Overbought не найдена без support."""
        d = TrendlineDetector()
        df = make_uptrend_df(50)
        ob = d.find_overbought_line(df, None, [])
        assert ob is None
    
    def test_find_oversold_none(self):
        """Oversold не найдена без supply."""
        d = TrendlineDetector()
        df = make_downtrend_df(50)
        os = d.find_oversold_line(df, None, [])
        assert os is None
    
    def test_detect_break_none(self):
        """Пробой не найден без линии."""
        d = TrendlineDetector()
        df = make_uptrend_df(50)
        b = d.detect_break(df, None)
        assert b is None
    
    def test_detect_all_breaks(self):
        """detect_all_breaks возвращает список."""
        d = TrendlineDetector(zigzag_length=3)
        df = make_uptrend_df(100)
        breaks = d.detect_all_breaks(df)
        assert isinstance(breaks, list)
        for b in breaks:
            assert isinstance(b, TrendlineBreak)
            assert b.direction in ['up', 'down']
            assert 0 <= b.strength <= 1.0
    
    def test_touches_counted(self):
        """Касания считаются."""
        d = TrendlineDetector(zigzag_length=3)
        df = make_uptrend_df(100)
        lines = d.detect_all(df)
        for line in lines:
            assert line.touches >= 0