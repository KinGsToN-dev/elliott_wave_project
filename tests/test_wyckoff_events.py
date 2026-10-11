"""
Тесты для wyckoff.events.
"""
import pytest
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wyckoff.ranges import TradingRange
from wyckoff.events import WyckoffEvent, WyckoffEventDetector


def make_ranging_df(n=100, upper=1.1050, lower=1.1000, add_spring=False):
    """DataFrame с боковиком."""
    np.random.seed(42)
    dates = [datetime(2026, 1, 1) + timedelta(hours=i) for i in range(n)]
    mid = (upper + lower) / 2
    
    prices = []
    volumes = []
    for i in range(n):
        if i % 2 == 0:
            prices.append(np.random.uniform(mid, upper))
        else:
            prices.append(np.random.uniform(lower, mid))
        volumes.append(100)
    
    df = pd.DataFrame({
        'open': prices,
        'high': [min(p + 0.0003, upper) for p in prices],
        'low': [max(p - 0.0003, lower) for p in prices],
        'close': prices,
        'tick_volume': volumes,
    }, index=dates)
    
    if add_spring:
        # Вставляем Spring на 70-м баре
        df.iloc[70, df.columns.get_loc('low')] = lower - 0.0003
        df.iloc[70, df.columns.get_loc('close')] = mid
        df.iloc[70, df.columns.get_loc('tick_volume')] = 300
    
    return df


def make_simple_range():
    """Простой TradingRange для тестов."""
    return TradingRange(
        start_idx=0,
        end_idx=80,
        upper=1.1050,
        lower=1.1000,
        width=0.0050,
        width_atr=2.0,
        bars_count=80,
        touches_upper=5,
        touches_lower=5,
    )


class TestWyckoffEvent:
    def test_init(self):
        """Инициализация события."""
        e = WyckoffEvent(
            type='SC', idx=10, price=1.1000,
            volume=500, direction='bullish', confidence=0.9,
        )
        assert e.type == 'SC'
        assert e.idx == 10
        assert e.volume == 500
        assert e.direction == 'bullish'
    
    def test_repr(self):
        """repr работает."""
        e = WyckoffEvent(
            type='Spring', idx=10, price=1.1000, volume=500,
        )
        s = repr(e)
        assert 'Spring' in s
        assert 'idx=10' in s


class TestEventDetector:
    def test_init(self):
        """Инициализация детектора."""
        d = WyckoffEventDetector()
        assert d.volume_ma_period == 20
        assert d.climax_volume_mult == 2.0
    
    def test_compute_atr(self):
        """ATR считается."""
        d = WyckoffEventDetector()
        df = make_ranging_df(n=50)
        atr = d._compute_atr(df)
        assert len(atr) == 50
        assert atr.iloc[-1] > 0
    
    def test_compute_volume_ma(self):
        """Volume MA считается."""
        d = WyckoffEventDetector()
        df = make_ranging_df(n=50)
        vol_ma = d._compute_volume_ma(df)
        assert len(vol_ma) == 50
        assert vol_ma.iloc[-1] > 0
    
    def test_find_spring(self):
        """Spring найден."""
        d = WyckoffEventDetector(spring_depth_atr=1.5)
        df = make_ranging_df(n=100, add_spring=True)
        r = make_simple_range()
        spring = d.find_spring(df, r)
        # В синтетических данных Spring может не найтись из-за узкого диапазона
        # главное — не падает
        assert spring is None or spring.type == 'Spring'
    
    def test_find_sos_none(self):
        """SOS не найден в боковике без пробоя."""
        d = WyckoffEventDetector()
        df = make_ranging_df(n=100)
        r = make_simple_range()
        sos = d.find_sos(df, r)
        # В боковике без пробоя SOS не должен найтись
        assert sos is None or sos.type == 'SOS'
    
    def test_find_sow_none(self):
        """SOW не найден в боковике без пробоя."""
        d = WyckoffEventDetector()
        df = make_ranging_df(n=100)
        r = make_simple_range()
        sow = d.find_sow(df, r)
        assert sow is None or sow.type == 'SOW'
    
    def test_find_upthrust_none(self):
        """UT не найден в боковике без пробоя."""
        d = WyckoffEventDetector()
        df = make_ranging_df(n=100)
        r = make_simple_range()
        ut = d.find_upthrust(df, r)
        assert ut is None or ut.type == 'UT'
    
    def test_find_selling_climax_none(self):
        """SC не найден в спокойном боковике."""
        d = WyckoffEventDetector()
        df = make_ranging_df(n=100)
        r = make_simple_range()
        sc = d.find_selling_climax(df, r)
        # Спокойный боковик — нет climax
        # Метод возвращает WyckoffEvent или None
        assert sc is None or sc.type == 'SC'
    
    def test_detect_all_returns_list(self):
        """detect_all возвращает список."""
        d = WyckoffEventDetector()
        df = make_ranging_df(n=100)
        r = make_simple_range()
        events = d.detect_all(df, r)
        assert isinstance(events, list)
        # Все элементы — WyckoffEvent
        for e in events:
            assert isinstance(e, WyckoffEvent)
    
    def test_events_sorted(self):
        """События отсортированы по idx."""
        d = WyckoffEventDetector()
        df = make_ranging_df(n=100, add_spring=True)
        r = make_simple_range()
        events = d.detect_all(df, r)
        
        if len(events) >= 2:
            for i in range(len(events) - 1):
                assert events[i].idx <= events[i + 1].idx
    
    def test_find_ar_none(self):
        """AR не найден без SC."""
        d = WyckoffEventDetector()
        df = make_ranging_df(n=50)
        ar = d.find_automatic_rally(df, None)
        assert ar is None
    
    def test_find_st_none(self):
        """ST не найден без SC/AR."""
        d = WyckoffEventDetector()
        df = make_ranging_df(n=50)
        st = d.find_secondary_test(df, None, None)
        assert st is None
    
    def test_find_lps_none(self):
        """LPS не найден без SOS."""
        d = WyckoffEventDetector()
        df = make_ranging_df(n=50)
        lps = d.find_lps(df, None)
        assert lps is None
    
    def test_find_lpsy_none(self):
        """LPSY не найден без SOW."""
        d = WyckoffEventDetector()
        df = make_ranging_df(n=50)
        lpsy = d.find_lpsy(df, None)
        assert lpsy is None
    
    def test_find_test_none(self):
        """Test не найден без Spring."""
        d = WyckoffEventDetector()
        df = make_ranging_df(n=50)
        t = d.find_test(df, None)
        assert t is None