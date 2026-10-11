"""
Тесты для wyckoff.relative_strength.
"""
import pytest
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wyckoff.ranges import TradingRange
from wyckoff.relative_strength import (
    RSResult, RSAtRange, RelativeStrengthAnalyzer,
)


def make_df(n=100, start=1.1000, step=0.0002):
    """DataFrame с заданным трендом."""
    np.random.seed(42)
    dates = [datetime(2026, 1, 1) + timedelta(hours=i) for i in range(n)]
    prices = [start + i * step + np.random.randn() * 0.0002 for i in range(n)]
    
    return pd.DataFrame({
        'open': prices,
        'high': [p + 0.0005 for p in prices],
        'low': [p - 0.0005 for p in prices],
        'close': prices,
        'tick_volume': [100] * n,
    }, index=dates)


class TestRSResult:
    def test_init(self):
        """Инициализация."""
        r = RSResult(
            rs_value=1.02, rs_trend='rising', rs_rank=85.0,
            is_stronger=True, rs_change_pct=2.5, period_bars=20,
        )
        assert r.rs_value == 1.02
        assert r.rs_trend == 'rising'
        assert r.is_stronger is True
    
    def test_repr(self):
        """repr."""
        r = RSResult(
            rs_value=1.02, rs_trend='rising', rs_rank=85.0,
            is_stronger=True, rs_change_pct=2.5, period_bars=20,
        )
        s = repr(r)
        assert 'rising' in s
        assert 'stronger=True' in s


class TestRSAtRange:
    def test_init(self):
        """Инициализация."""
        r = TradingRange(
            start_idx=0, end_idx=50,
            upper=1.1050, lower=1.1000,
            width=0.005, width_atr=2.0, bars_count=50,
        )
        rsr = RSAtRange(
            range_obj=r, rs_before=1.0, rs_after=1.05,
            rs_in_range=1.02, trend='rising',
            behavior_at_highs='stronger',
            behavior_at_lows='stronger',
            interpretation='СИЛЬНЫЙ',
        )
        assert rsr.trend == 'rising'
        assert rsr.behavior_at_highs == 'stronger'
    
    def test_repr(self):
        """repr."""
        r = TradingRange(
            start_idx=0, end_idx=50,
            upper=1.1050, lower=1.1000,
            width=0.005, width_atr=2.0, bars_count=50,
        )
        rsr = RSAtRange(
            range_obj=r, rs_before=1.0, rs_after=1.05,
            rs_in_range=1.02, trend='rising',
            behavior_at_highs='stronger',
            behavior_at_lows='stronger',
            interpretation='СИЛЬНЫЙ',
        )
        s = repr(rsr)
        assert 'rising' in s


class TestRelativeStrengthAnalyzer:
    def test_init(self):
        """Инициализация."""
        a = RelativeStrengthAnalyzer()
        assert a.trend_period == 20
        assert a.flat_threshold == 0.002
    
    def test_validate_data_none(self):
        """None данные."""
        a = RelativeStrengthAnalyzer()
        assert a._validate_data(None, None) is False
    
    def test_validate_data_missing_columns(self):
        """Нет колонки close."""
        a = RelativeStrengthAnalyzer()
        df1 = pd.DataFrame({'price': [1, 2, 3]})
        df2 = pd.DataFrame({'close': [1, 2, 3]})
        assert a._validate_data(df1, df2) is False
    
    def test_validate_data_empty(self):
        """Пустые данные."""
        a = RelativeStrengthAnalyzer()
        df1 = pd.DataFrame({'close': [1]})
        df2 = pd.DataFrame({'close': [1]})
        assert a._validate_data(df1, df2) is False
    
    def test_validate_data_valid(self):
        """Корректные данные."""
        a = RelativeStrengthAnalyzer()
        df1 = make_df(50)
        df2 = make_df(50)
        assert a._validate_data(df1, df2) is True
    
    def test_compute_rs(self):
        """RS считается."""
        a = RelativeStrengthAnalyzer()
        df1 = make_df(50, start=1.1000, step=0.0003)
        df2 = make_df(50, start=1.1000, step=0.0001)
        
        rs = a.compute_rs(df1, df2)
        assert rs is not None
        assert len(rs) == 50
        # Актив растёт быстрее → RS растёт
        assert rs.iloc[-1] > rs.iloc[0]
    
    def test_compute_rs_same(self):
        """Одинаковые данные → RS ≈ 1."""
        a = RelativeStrengthAnalyzer()
        df = make_df(50)
        rs = a.compute_rs(df, df)
        assert rs is not None
        assert abs(rs.iloc[-1] - 1.0) < 1e-6
    
    def test_find_rs_trend_rising(self):
        """RS растёт."""
        a = RelativeStrengthAnalyzer(trend_period=20)
        rs = pd.Series([1.0 + i * 0.001 for i in range(50)])
        trend = a.find_rs_trend(rs)
        assert trend == 'rising'
    
    def test_find_rs_trend_falling(self):
        """RS падает."""
        a = RelativeStrengthAnalyzer(trend_period=20)
        rs = pd.Series([1.05 - i * 0.001 for i in range(50)])
        trend = a.find_rs_trend(rs)
        assert trend == 'falling'
    
    def test_find_rs_trend_flat(self):
        """RS флэт."""
        a = RelativeStrengthAnalyzer(trend_period=20, flat_threshold=0.05)
        rs = pd.Series([1.0 + np.random.randn() * 0.001 for _ in range(50)])
        trend = a.find_rs_trend(rs)
        assert trend in ['flat', 'rising', 'falling']
    
    def test_find_rs_trend_empty(self):
        """Пустой RS."""
        a = RelativeStrengthAnalyzer()
        trend = a.find_rs_trend(pd.Series([], dtype=float))
        assert trend == 'flat'
    
    def test_find_rs_rank_max(self):
        """RS на максимуме → rank ≈ 100."""
        a = RelativeStrengthAnalyzer(rank_period=20)
        rs = pd.Series([1.0 + i * 0.001 for i in range(50)])
        rank = a.find_rs_rank(rs)
        assert rank >= 90.0
    
    def test_find_rs_rank_min(self):
        """RS на минимуме → rank ≈ 0."""
        a = RelativeStrengthAnalyzer(rank_period=20)
        rs = pd.Series([1.05 - i * 0.001 for i in range(50)])
        rank = a.find_rs_rank(rs)
        assert rank <= 10.0
    
    def test_find_rs_rank_empty(self):
        """Пустой RS → 50."""
        a = RelativeStrengthAnalyzer()
        rank = a.find_rs_rank(pd.Series([], dtype=float))
        assert rank == 50.0
    
    def test_analyze_stronger(self):
        """Анализ сильного актива."""
        a = RelativeStrengthAnalyzer(trend_period=20, rank_period=50)
        asset = make_df(100, start=1.1000, step=0.0003)
        benchmark = make_df(100, start=1.1000, step=0.0001)
        
        result = a.analyze(asset, benchmark)
        assert result is not None
        assert result.is_stronger is True
        assert result.rs_trend == 'rising'
    
    def test_analyze_weaker(self):
        """Анализ слабого актива."""
        a = RelativeStrengthAnalyzer(trend_period=20, rank_period=50)
        asset = make_df(100, start=1.1000, step=0.00005)
        benchmark = make_df(100, start=1.1000, step=0.0003)
        
        result = a.analyze(asset, benchmark)
        assert result is not None
        assert result.is_stronger is False
        assert result.rs_trend == 'falling'
    
    def test_analyze_invalid_data(self):
        """Невалидные данные → None."""
        a = RelativeStrengthAnalyzer()
        result = a.analyze(None, None)
        assert result is None
    
    def test_compare_at_range(self):
        """Сравнение в Trading Range."""
        a = RelativeStrengthAnalyzer(trend_period=10)
        asset = make_df(100, start=1.1000, step=0.0003)
        benchmark = make_df(100, start=1.1000, step=0.0001)
        
        r = TradingRange(
            start_idx=20, end_idx=70,
            upper=1.1100, lower=1.1050,
            width=0.005, width_atr=2.0, bars_count=50,
        )
        
        result = a.compare_at_range(asset, benchmark, r)
        assert result is not None
        assert isinstance(result, RSAtRange)
        assert result.trend in ['rising', 'falling', 'flat']
        assert result.behavior_at_highs in ['stronger', 'weaker', 'same']
        assert result.behavior_at_lows in ['stronger', 'weaker', 'same']
        assert len(result.interpretation) > 0
    
    def test_compare_at_range_invalid(self):
        """Сравнение с невалидными данными → None."""
        a = RelativeStrengthAnalyzer()
        r = TradingRange(
            start_idx=0, end_idx=10,
            upper=1.1, lower=1.0,
            width=0.1, width_atr=1.0, bars_count=10,
        )
        result = a.compare_at_range(None, None, r)
        assert result is None
    
    def test_find_strongest(self):
        """Поиск самого сильного актива."""
        a = RelativeStrengthAnalyzer(trend_period=20, rank_period=50)
        
        benchmark = make_df(100, start=1.1000, step=0.0001)
        assets = {
            'STRONG': make_df(100, start=1.1000, step=0.0005),
            'WEAK': make_df(100, start=1.1000, step=0.00001),
            'MEDIUM': make_df(100, start=1.1000, step=0.0002),
        }
        
        results = a.find_strongest(assets, benchmark)
        assert len(results) == 3
        # Самый сильный первый
        assert results[0][0] == 'STRONG'
        # Самый слабый последний
        assert results[-1][0] == 'WEAK'
    
    def test_find_strongest_empty(self):
        """Пустой список активов."""
        a = RelativeStrengthAnalyzer()
        benchmark = make_df(50)
        results = a.find_strongest({}, benchmark)
        assert results == []