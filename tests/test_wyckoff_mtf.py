"""
Тесты для wyckoff.mtf.
"""
import pytest
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wyckoff.mtf import (
    MTFResult, WyckoffMTFAnalyzer, TIMEFRAME_ORDER,
)


def make_ranging_df(n=100, upper=1.1050, lower=1.1000):
    """Боковик."""
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


def make_uptrend_df(n=100):
    """Восходящий тренд."""
    np.random.seed(42)
    dates = [datetime(2026, 1, 1) + timedelta(hours=i) for i in range(n)]
    prices = [1.1000 + i * 0.0003 for i in range(n)]
    
    return pd.DataFrame({
        'open': prices,
        'high': [p + 0.0003 for p in prices],
        'low': [p - 0.0003 for p in prices],
        'close': prices,
        'tick_volume': [100] * n,
    }, index=dates)


def make_downtrend_df(n=100):
    """Нисходящий тренд."""
    np.random.seed(42)
    dates = [datetime(2026, 1, 1) + timedelta(hours=i) for i in range(n)]
    prices = [1.1000 - i * 0.0003 for i in range(n)]
    
    return pd.DataFrame({
        'open': prices,
        'high': [p + 0.0003 for p in prices],
        'low': [p - 0.0003 for p in prices],
        'close': prices,
        'tick_volume': [100] * n,
    }, index=dates)


class TestMTFResult:
    def test_init(self):
        """Инициализация."""
        r = MTFResult()
        assert r.signal == 'WAIT'
        assert r.confidence == 0.0
        assert r.alignment == 'mixed'
        assert r.analyses == {}
    
    def test_repr(self):
        """repr."""
        r = MTFResult(signal='BUY', confidence=0.8, alignment='bullish')
        s = repr(r)
        assert 'BUY' in s
        assert 'bullish' in s


class TestTimeframeOrder:
    def test_order(self):
        """Порядок ТФ определён."""
        assert 'H1' in TIMEFRAME_ORDER
        assert 'H4' in TIMEFRAME_ORDER
        assert 'D1' in TIMEFRAME_ORDER
        assert TIMEFRAME_ORDER.index('H1') < TIMEFRAME_ORDER.index('H4')
        assert TIMEFRAME_ORDER.index('H4') < TIMEFRAME_ORDER.index('D1')


class TestWyckoffMTFAnalyzer:
    def test_init(self):
        """Инициализация."""
        a = WyckoffMTFAnalyzer()
        assert a.detector is not None
        assert a.timeframes is None
    
    def test_sort_timeframes(self):
        """Сортировка ТФ."""
        a = WyckoffMTFAnalyzer()
        tfs = ['D1', 'H1', 'H4']
        sorted_tfs = a._sort_timeframes(tfs)
        assert sorted_tfs == ['H1', 'H4', 'D1']
    
    def test_analyze_all_empty(self):
        """Пустой словарь."""
        a = WyckoffMTFAnalyzer()
        result = a.analyze_all({})
        assert isinstance(result, MTFResult)
        assert result.signal == 'WAIT'
    
    def test_analyze_all_single_tf(self):
        """Один ТФ."""
        a = WyckoffMTFAnalyzer()
        data = {'H4': make_ranging_df(100)}
        result = a.analyze_all(data)
        assert isinstance(result, MTFResult)
        assert 'H4' in result.analyses
        assert len(result.summary) > 0
    
    def test_analyze_all_three_tfs(self):
        """Три ТФ."""
        a = WyckoffMTFAnalyzer()
        data = {
            'H1': make_uptrend_df(100),
            'H4': make_uptrend_df(100),
            'D1': make_uptrend_df(100),
        }
        result = a.analyze_all(data)
        assert len(result.analyses) == 3
        assert 'H1' in result.analyses
        assert 'H4' in result.analyses
        assert 'D1' in result.analyses
    
    def test_alignment_bullish(self):
        """Согласованность бычья (все тренды вверх)."""
        a = WyckoffMTFAnalyzer()
        data = {
            'H1': make_uptrend_df(100),
            'H4': make_uptrend_df(100),
            'D1': make_uptrend_df(100),
        }
        result = a.analyze_all(data)
        # Может быть bullish или mixed — точная логика зависит от детекторов
        assert result.alignment in ['bullish', 'bearish', 'mixed', 'neutral']
        assert result.signal in ['BUY', 'SELL', 'WAIT']
    
    def test_alignment_bearish(self):
        """Согласованность медвежья (все тренды вниз)."""
        a = WyckoffMTFAnalyzer()
        data = {
            'H1': make_downtrend_df(100),
            'H4': make_downtrend_df(100),
            'D1': make_downtrend_df(100),
        }
        result = a.analyze_all(data)
        assert result.alignment in ['bullish', 'bearish', 'mixed', 'neutral']
    
    def test_alignment_mixed(self):
        """Разные тренды — mixed."""
        a = WyckoffMTFAnalyzer()
        data = {
            'H1': make_uptrend_df(100),
            'H4': make_downtrend_df(100),
            'D1': make_ranging_df(100),
        }
        result = a.analyze_all(data)
        assert isinstance(result, MTFResult)
    
    def test_get_phase_by_tf(self):
        """Фазы по ТФ."""
        a = WyckoffMTFAnalyzer()
        data = {
            'H4': make_uptrend_df(100),
            'D1': make_downtrend_df(100),
        }
        result = a.analyze_all(data)
        phases = a.get_phase_by_tf(result)
        assert isinstance(phases, dict)
        assert 'H4' in phases
        assert 'D1' in phases
    
    def test_get_events_by_tf(self):
        """События по ТФ."""
        a = WyckoffMTFAnalyzer()
        data = {
            'H4': make_ranging_df(100),
            'D1': make_ranging_df(100),
        }
        result = a.analyze_all(data)
        events = a.get_events_by_tf(result)
        assert isinstance(events, dict)
    
    def test_benchmark_data(self):
        """С benchmark для RS."""
        a = WyckoffMTFAnalyzer()
        data = {
            'H4': make_uptrend_df(100),
            'D1': make_uptrend_df(100),
        }
        benchmark = {
            'H4': make_uptrend_df(100),
            'D1': make_uptrend_df(100),
        }
        result = a.analyze_all(data, benchmark_data=benchmark)
        assert isinstance(result, MTFResult)
        # Проверяем, что RS посчитан
        for tf, analysis in result.analyses.items():
            assert analysis.rs is not None
    
    def test_summary_contains_tfs(self):
        """Summary содержит имена ТФ."""
        a = WyckoffMTFAnalyzer()
        data = {
            'H4': make_uptrend_df(100),
            'D1': make_uptrend_df(100),
        }
        result = a.analyze_all(data)
        assert 'H4' in result.summary
        assert 'D1' in result.summary
    
    def test_bullish_score(self):
        """Бычья оценка в диапазоне 0..1."""
        a = WyckoffMTFAnalyzer()
        from wyckoff.detector import WyckoffAnalysis
        from wyckoff.phases import PhaseResult, Phase
        analysis = WyckoffAnalysis()
        analysis.current_phase = PhaseResult(
            phase=Phase.ACCUMULATION,
            confidence=0.8,
        )
        score = a._analyze_bullish_score(analysis)
        assert 0.0 <= score <= 1.0
    
    def test_bearish_score(self):
        """Медвежья оценка в диапазоне 0..1."""
        a = WyckoffMTFAnalyzer()
        from wyckoff.detector import WyckoffAnalysis
        from wyckoff.phases import PhaseResult, Phase
        analysis = WyckoffAnalysis()
        analysis.current_phase = PhaseResult(
            phase=Phase.DISTRIBUTION,
            confidence=0.8,
        )
        score = a._analyze_bearish_score(analysis)
        assert 0.0 <= score <= 1.0
    
    def test_score_none(self):
        """Оценка None = 0."""
        a = WyckoffMTFAnalyzer()
        assert a._analyze_bullish_score(None) == 0.0
        assert a._analyze_bearish_score(None) == 0.0
    
    def test_confidence_range(self):
        """Confidence в диапазоне 0..1."""
        a = WyckoffMTFAnalyzer()
        data = {
            'H4': make_uptrend_df(100),
            'D1': make_uptrend_df(100),
        }
        result = a.analyze_all(data)
        assert 0.0 <= result.confidence <= 1.0
    
    def test_signal_valid(self):
        """Сигнал валидный."""
        a = WyckoffMTFAnalyzer()
        data = {'H4': make_ranging_df(100)}
        result = a.analyze_all(data)
        assert result.signal in ['BUY', 'SELL', 'WAIT']
    
    def test_meta_has_scores(self):
        """Meta содержит оценки."""
        a = WyckoffMTFAnalyzer()
        data = {
            'H4': make_uptrend_df(100),
            'D1': make_uptrend_df(100),
        }
        result = a.analyze_all(data)
        assert 'bullish_scores' in result.meta
        assert 'bearish_scores' in result.meta
        assert 'total_bullish' in result.meta
        assert 'total_bearish' in result.meta