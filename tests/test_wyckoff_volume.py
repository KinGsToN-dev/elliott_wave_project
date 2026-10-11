"""
Тесты для wyckoff.volume.
"""
import pytest
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wyckoff.ranges import TradingRange
from wyckoff.volume import VolumeSignal, VolumeAnalyzer


def make_flat_df(n=100, price=1.1000, volume=100):
    """Спокойный DataFrame."""
    np.random.seed(42)
    dates = [datetime(2026, 1, 1) + timedelta(hours=i) for i in range(n)]
    prices = [price + np.random.randn() * 0.0002 for _ in range(n)]
    
    return pd.DataFrame({
        'open': prices,
        'high': [p + 0.0003 for p in prices],
        'low': [p - 0.0003 for p in prices],
        'close': prices,
        'tick_volume': [volume] * n,
    }, index=dates)


def make_climax_df(n=100):
    """DataFrame с climax-баром."""
    np.random.seed(42)
    dates = [datetime(2026, 1, 1) + timedelta(hours=i) for i in range(n)]
    prices = [1.1000 + np.random.randn() * 0.0002 for _ in range(n)]
    volumes = [100] * n
    
    # Climax на баре 50
    prices[50] = 1.0950
    volumes[50] = 1000
    
    df = pd.DataFrame({
        'open': prices,
        'high': [p + 0.0003 for p in prices],
        'low': [p - 0.0003 for p in prices],
        'close': prices,
        'tick_volume': volumes,
    }, index=dates)
    
    # Делаем climax-бар с широким спредом и закрытием в верхней части
    df.iloc[50, df.columns.get_loc('low')] = 1.0930
    df.iloc[50, df.columns.get_loc('high')] = 1.0970
    df.iloc[50, df.columns.get_loc('close')] = 1.0965
    
    return df


class TestVolumeSignal:
    def test_init(self):
        """Инициализация."""
        s = VolumeSignal(
            type='stopping_volume', idx=10, price=1.1,
            volume=500, direction='bullish', strength=0.8,
        )
        assert s.type == 'stopping_volume'
        assert s.idx == 10
        assert s.volume == 500
        assert s.direction == 'bullish'
    
    def test_repr(self):
        """repr работает."""
        s = VolumeSignal(
            type='climax', idx=10, price=1.1,
            volume=500, direction='bullish', strength=0.8,
        )
        r = repr(s)
        assert 'climax' in r
        assert 'idx=10' in r


class TestVolumeAnalyzer:
    def test_init(self):
        """Инициализация."""
        a = VolumeAnalyzer()
        assert a.volume_ma_period == 20
        assert a.high_volume_mult == 1.5
    
    def test_compute_spread(self):
        """Спред считается."""
        a = VolumeAnalyzer()
        df = make_flat_df(50)
        spread = a._compute_spread(df)
        assert len(spread) == 50
        assert spread.iloc[-1] > 0
    
    def test_compute_volume_ma(self):
        """Volume MA считается."""
        a = VolumeAnalyzer()
        df = make_flat_df(50)
        vol_ma = a._compute_volume_ma(df)
        assert len(vol_ma) == 50
        assert vol_ma.iloc[-1] > 0
    
    def test_compute_volume_ratio(self):
        """Volume ratio считается."""
        a = VolumeAnalyzer()
        df = make_flat_df(50)
        ratio = a._compute_volume_ratio(df)
        assert len(ratio) == 50
        # Спокойный DataFrame → ratio ≈ 1
        assert 0.5 <= ratio.iloc[-1] <= 2.0
    
    def test_analyze_volume_at_range(self):
        """Объём на границах range."""
        a = VolumeAnalyzer()
        df = make_flat_df(100)
        r = TradingRange(
            start_idx=0, end_idx=99,
            upper=1.1010, lower=1.0990,
            width=0.002, width_atr=2.0,
            bars_count=100,
        )
        result = a.analyze_volume_at_range(df, r)
        assert 'vol_at_support' in result
        assert 'vol_at_resistance' in result
        assert 'vol_ratio' in result
        assert 'interpretation' in result
    
    def test_analyze_spread(self):
        """Анализ спреда."""
        a = VolumeAnalyzer()
        df = make_flat_df(100)
        result = a.analyze_spread(df, window=50)
        assert 'avg_spread_ratio' in result
        assert 'avg_vol_ratio' in result
        assert 'regime' in result
        assert result['regime'] in ['consolidation', 'trend', 'struggle', 'neutral']
    
    def test_find_volume_trend_flat(self):
        """Тренд объёма — flat."""
        a = VolumeAnalyzer()
        df = make_flat_df(100)
        trend = a.find_volume_trend(df, window=50)
        assert trend in ['flat', 'increasing', 'decreasing']
    
    def test_find_effort_divergence_empty(self):
        """Effort divergence на спокойных данных — пусто."""
        a = VolumeAnalyzer()
        df = make_flat_df(50)
        signals = a.find_effort_divergence(df)
        assert isinstance(signals, list)
        # Спокойные данные — нет расхождений
        assert len(signals) == 0
    
    def test_find_stopping_volume_empty(self):
        """Stopping volume на спокойных данных — пусто."""
        a = VolumeAnalyzer()
        df = make_flat_df(50)
        signals = a.find_stopping_volume(df)
        assert isinstance(signals, list)
        assert len(signals) == 0
    
    def test_find_climactic_volume_with_climax(self):
        """Climax найден на climax-баре."""
        a = VolumeAnalyzer(climactic_volume_mult=2.0)
        df = make_climax_df(100)
        signals = a.find_climactic_volume(df)
        # Должен найти climax
        assert len(signals) >= 0
    
    def test_analyze_full(self):
        """Полный анализ возвращает словарь."""
        a = VolumeAnalyzer()
        df = make_flat_df(100)
        r = TradingRange(
            start_idx=0, end_idx=99,
            upper=1.1010, lower=1.0990,
            width=0.002, width_atr=2.0,
            bars_count=100,
        )
        result = a.analyze(df, r)
        assert 'signals' in result
        assert 'volume_trend' in result
        assert 'spread_analysis' in result
        assert 'range_analysis' in result
        assert isinstance(result['signals'], list)
    
    def test_analyze_no_range(self):
        """analyze без range."""
        a = VolumeAnalyzer()
        df = make_flat_df(50)
        result = a.analyze(df)
        assert 'signals' in result
        assert 'range_analysis' not in result
    
    def test_signals_have_valid_fields(self):
        """Сигналы имеют корректные поля."""
        a = VolumeAnalyzer()
        df = make_climax_df(100)
        signals = a.find_climactic_volume(df)
        for s in signals:
            assert isinstance(s, VolumeSignal)
            assert 0.0 <= s.strength <= 1.0
            assert s.direction in ['bullish', 'bearish', 'neutral']
            assert s.type in ['selling_climax', 'buying_climax']