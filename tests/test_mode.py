"""
Тесты для core.mode_loader и core.mtf_filter.
"""
import pytest
import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.mode_loader import get_mode, list_modes, load_modes
from core.mtf_filter import MTFFilter


def make_df(n=200, trend='up'):
    np.random.seed(42)
    dates = [datetime(2026, 1, 1) + timedelta(hours=i) for i in range(n)]
    if trend == 'up':
        base = np.linspace(1.1000, 1.1500, n)
    elif trend == 'down':
        base = np.linspace(1.1500, 1.1000, n)
    else:
        base = np.ones(n) * 1.1000
    noise = np.random.randn(n) * 0.0005
    prices = base + noise
    return pd.DataFrame({
        'open': prices, 'high': prices + 0.0003, 'low': prices - 0.0003,
        'close': prices, 'tick_volume': [100] * n,
    }, index=dates)


class TestModeLoader:
    def test_load_modes(self):
        modes = load_modes()
        assert 'swing' in modes
        assert 'position' in modes
        assert 'intraday' in modes
    
    def test_get_swing(self):
        mode = get_mode('swing')
        assert mode['name'] == 'Свинг (H4/D1)'
        assert mode['timeframes'] == ['H4', 'D1']
        assert mode['use_mtf_filter'] == False
    
    def test_get_intraday(self):
        mode = get_mode('intraday')
        assert mode['name'] == 'Интрадей (M30/H1)'
        assert mode['timeframes'] == ['M30', 'H1']
        assert mode['use_mtf_filter'] == True
        assert mode['mtf_timeframe'] == 'H4'
    
    def test_get_unknown_mode(self):
        with pytest.raises(ValueError):
            get_mode('unknown')
    
    def test_list_modes(self):
        modes = list_modes()
        assert 'swing' in modes
        assert 'intraday' in modes
        assert len(modes) >= 3


class TestMTFFilter:
    def test_init(self):
        f = MTFFilter(mtf_timeframe='H4')
        assert f.mtf_timeframe == 'H4'
        assert f.trend == 'UNKNOWN'
    
    def test_update_trend_bullish(self):
        f = MTFFilter()
        df = make_df(200, 'up')
        f.update_trend(df)
        assert f.trend in ['BULLISH', 'NEUTRAL']
    
    def test_update_trend_bearish(self):
        f = MTFFilter()
        df = make_df(200, 'down')
        f.update_trend(df)
        assert f.trend in ['BEARISH', 'NEUTRAL']
    
    def test_update_trend_empty(self):
        f = MTFFilter()
        f.update_trend(None)
        assert f.trend == 'UNKNOWN'
    
    def test_filter_bullish(self):
        f = MTFFilter()
        f.trend = 'BULLISH'
        signals = [
            {'direction': 'BUY'},
            {'direction': 'SELL'},
            {'direction': 'BUY'},
        ]
        filtered = f.filter_signals(signals)
        assert len(filtered) == 2
        assert all(s['direction'] == 'BUY' for s in filtered)
    
    def test_filter_bearish(self):
        f = MTFFilter()
        f.trend = 'BEARISH'
        signals = [
            {'direction': 'BUY'},
            {'direction': 'SELL'},
            {'direction': 'SELL'},
        ]
        filtered = f.filter_signals(signals)
        assert len(filtered) == 2
        assert all(s['direction'] == 'SELL' for s in filtered)
    
    def test_filter_unknown(self):
        f = MTFFilter()
        f.trend = 'UNKNOWN'
        signals = [{'direction': 'BUY'}, {'direction': 'SELL'}]
        filtered = f.filter_signals(signals)
        assert len(filtered) == 2  # нет фильтра
    
    def test_get_summary(self):
        f = MTFFilter()
        df = make_df(200, 'up')
        f.update_trend(df)
        summary = f.get_summary()
        assert 'trend' in summary
        assert 'ema_value' in summary
        assert 'current_price' in summary
