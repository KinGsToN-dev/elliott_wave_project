"""
Тесты для wyckoff.detector (фасад).
"""
import pytest
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wyckoff.detector import WyckoffDetector, WyckoffAnalysis
from wyckoff.phases import Phase


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


def make_trending_df(n=100, direction='up'):
    """DataFrame с трендом."""
    np.random.seed(42)
    dates = [datetime(2026, 1, 1) + timedelta(hours=i) for i in range(n)]
    
    if direction == 'up':
        prices = [1.1000 + i * 0.0005 for i in range(n)]
    else:
        prices = [1.1000 - i * 0.0005 for i in range(n)]
    
    return pd.DataFrame({
        'open': prices,
        'high': [p + 0.0003 for p in prices],
        'low': [p - 0.0003 for p in prices],
        'close': prices,
        'tick_volume': [100] * n,
    }, index=dates)


class TestWyckoffAnalysis:
    def test_init(self):
        """Инициализация."""
        a = WyckoffAnalysis()
        assert a.ranges == []
        assert a.events == []
        assert a.summary == ''
    
    def test_repr(self):
        """repr."""
        a = WyckoffAnalysis()
        s = repr(a)
        assert 'WyckoffAnalysis' in s
        assert 'ranges=0' in s
    
    def test_to_dict(self):
        """to_dict."""
        a = WyckoffAnalysis()
        d = a.to_dict()
        assert 'ranges_count' in d
        assert 'events' in d
        assert 'phase' in d
        assert 'rs' in d
    
    def test_get_bullish_events_empty(self):
        """Пустой список бычьих."""
        a = WyckoffAnalysis()
        assert a.get_bullish_events() == []
    
    def test_get_bearish_events_empty(self):
        """Пустой список медвежьих."""
        a = WyckoffAnalysis()
        assert a.get_bearish_events() == []
    
    def test_has_phase_no_phase(self):
        """has_phase при отсутствии фазы."""
        a = WyckoffAnalysis()
        assert a.has_phase(Phase.ACCUMULATION) is False


class TestWyckoffDetector:
    def test_init(self):
        """Инициализация."""
        d = WyckoffDetector()
        assert d.range_detector is not None
        assert d.event_detector is not None
        assert d.phase_detector is not None
        assert d.volume_analyzer is not None
        assert d.trendline_detector is not None
        assert d.rs_analyzer is not None
    
    def test_detect_all_empty(self):
        """Пустой DataFrame."""
        d = WyckoffDetector()
        result = d.detect_all(None)
        assert isinstance(result, WyckoffAnalysis)
        assert result.summary == 'Not enough data'
    
    def test_detect_all_short(self):
        """Мало баров."""
        d = WyckoffDetector()
        df = pd.DataFrame({
            'high': [1.1] * 10,
            'low': [1.0] * 10,
            'close': [1.05] * 10,
            'tick_volume': [100] * 10,
        })
        result = d.detect_all(df)
        assert result.summary == 'Not enough data'
    
    def test_detect_all_ranging(self):
        """Анализ на боковике."""
        d = WyckoffDetector()
        df = make_ranging_df(100)
        result = d.detect_all(df)
        assert isinstance(result, WyckoffAnalysis)
        assert len(result.summary) > 0
    
    def test_detect_all_trending(self):
        """Анализ на тренде."""
        d = WyckoffDetector()
        df = make_trending_df(100, direction='up')
        result = d.detect_all(df)
        assert isinstance(result, WyckoffAnalysis)
    
    def test_detect_all_with_benchmark(self):
        """Анализ с benchmark для RS."""
        d = WyckoffDetector()
        df = make_trending_df(100, direction='up')
        benchmark = make_trending_df(100, direction='up')
        
        result = d.detect_all(df, benchmark_df=benchmark)
        assert result.rs is not None
        assert result.rs.rs_trend in ['rising', 'falling', 'flat']
    
    def test_detect_all_without_benchmark(self):
        """Без benchmark RS = None."""
        d = WyckoffDetector()
        df = make_ranging_df(100)
        result = d.detect_all(df)
        assert result.rs is None
    
    def test_summary_not_empty(self):
        """Summary не пустой."""
        d = WyckoffDetector()
        df = make_ranging_df(100)
        result = d.detect_all(df)
        assert len(result.summary) > 0
    
    def test_summary_has_content(self):
        """Summary содержит информацию."""
        d = WyckoffDetector()
        df = make_ranging_df(100)
        result = d.detect_all(df)
        # Должен быть хотя бы какой-то раздел
        assert 'Phase' in result.summary or 'No signals' in result.summary
    
    def test_quick_scan(self):
        """quick_scan возвращает компактный словарь."""
        d = WyckoffDetector()
        df = make_ranging_df(100)
        scan = d.quick_scan(df)
        
        assert isinstance(scan, dict)
        assert 'phase' in scan
        assert 'has_range' in scan
        assert 'bullish_events' in scan
        assert 'bearish_events' in scan
        assert 'summary' in scan
    
    def test_quick_scan_empty(self):
        """quick_scan на пустых данных."""
        d = WyckoffDetector()
        scan = d.quick_scan(None)
        assert isinstance(scan, dict)
    
    def test_analysis_repr(self):
        """repr анализа."""
        d = WyckoffDetector()
        df = make_ranging_df(100)
        result = d.detect_all(df)
        s = repr(result)
        assert 'WyckoffAnalysis' in s
    
    def test_analysis_to_dict_full(self):
        """to_dict полный."""
        d = WyckoffDetector()
        df = make_ranging_df(100)
        benchmark = make_trending_df(100)
        result = d.detect_all(df, benchmark_df=benchmark)
        
        d_dict = result.to_dict()
        assert d_dict['ranges_count'] >= 0
        assert isinstance(d_dict['events'], list)
        assert 'rs' in d_dict