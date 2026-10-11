"""
Тесты для Wyckoff-стратегий.
"""
import pytest
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.strategies import list_strategies, get_strategy
from backtest.strategies.wyckoff_base import WyckoffBaseStrategy
from backtest.strategies.wyckoff_spring import WyckoffSpringStrategy
from backtest.strategies.wyckoff_sos import WyckoffSOSStrategy
from backtest.strategies.wyckoff_utad import WyckoffUTADStrategy
from backtest.strategies.wyckoff_sow import WyckoffSOWStrategy
from backtest.strategies.wyckoff_combined import WyckoffCombinedStrategy

from wyckoff.detector import WyckoffAnalysis
from wyckoff.phases import Phase, PhaseResult
from wyckoff.events import WyckoffEvent


def make_df(n=100):
    """Простой DataFrame."""
    np.random.seed(42)
    dates = [datetime(2026, 1, 1) + timedelta(hours=i) for i in range(n)]
    prices = [1.1000 + np.random.randn() * 0.001 for _ in range(n)]
    
    return pd.DataFrame({
        'open': prices,
        'high': [p + 0.0005 for p in prices],
        'low': [p - 0.0005 for p in prices],
        'close': prices,
        'tick_volume': [100] * n,
    }, index=dates)


def make_analysis_with_phase(phase, confidence=0.8, events=None):
    """Создаёт WyckoffAnalysis с фазой и событиями."""
    analysis = WyckoffAnalysis()
    analysis.current_phase = PhaseResult(
        phase=phase,
        confidence=confidence,
        reason='test',
    )
    if events:
        analysis.events = events
    return analysis


def make_event(event_type, idx=50, price=1.1, direction='bullish'):
    """Создаёт WyckoffEvent."""
    return WyckoffEvent(
        type=event_type,
        idx=idx,
        price=price,
        volume=200,
        direction=direction,
        confidence=0.8,
    )


class TestStrategyRegistry:
    def test_all_wyckoff_strategies_registered(self):
        """Все Wyckoff-стратегии в реестре."""
        strategies = list_strategies()
        assert 'wyckoff_spring' in strategies
        assert 'wyckoff_sos' in strategies
        assert 'wyckoff_utad' in strategies
        assert 'wyckoff_sow' in strategies
        assert 'wyckoff_combined' in strategies
    
    def test_get_spring(self):
        """get_strategy('wyckoff_spring')."""
        cls = get_strategy('wyckoff_spring')
        assert cls is WyckoffSpringStrategy
    
    def test_get_sos(self):
        """get_strategy('wyckoff_sos')."""
        cls = get_strategy('wyckoff_sos')
        assert cls is WyckoffSOSStrategy
    
    def test_get_utad(self):
        """get_strategy('wyckoff_utad')."""
        cls = get_strategy('wyckoff_utad')
        assert cls is WyckoffUTADStrategy
    
    def test_get_sow(self):
        """get_strategy('wyckoff_sow')."""
        cls = get_strategy('wyckoff_sow')
        assert cls is WyckoffSOWStrategy
    
    def test_get_combined(self):
        """get_strategy('wyckoff_combined')."""
        cls = get_strategy('wyckoff_combined')
        assert cls is WyckoffCombinedStrategy
    
    def test_instantiate_all(self):
        """Все стратегии инстанцируются."""
        for name in ['wyckoff_spring', 'wyckoff_sos', 'wyckoff_utad',
                     'wyckoff_sow', 'wyckoff_combined']:
            cls = get_strategy(name)
            s = cls()
            assert s is not None
            assert s.name is not None


class TestWyckoffBaseStrategy:
    def test_init(self):
        """Инициализация."""
        s = WyckoffBaseStrategy()
        assert s.name == "Wyckoff Base"
        assert s.target_atr_mult == 2.0
        assert s.stop_atr_mult == 0.5
    
    def test_compute_atr(self):
        """ATR считается."""
        s = WyckoffBaseStrategy()
        df = make_df(50)
        atr = s._compute_atr(df)
        assert len(atr) == 50
        assert atr.iloc[-1] > 0
    
    def test_get_stop_buy(self):
        """Стоп для BUY."""
        s = WyckoffBaseStrategy(stop_atr_mult=1.0)
        df = make_df(50)
        analysis = WyckoffAnalysis()
        stop = s._get_stop(analysis, 40, df, 'BUY')
        entry = df.iloc[40]['close']
        assert stop < entry  # стоп ниже входа для BUY
    
    def test_get_stop_sell(self):
        """Стоп для SELL."""
        s = WyckoffBaseStrategy(stop_atr_mult=1.0)
        df = make_df(50)
        analysis = WyckoffAnalysis()
        stop = s._get_stop(analysis, 40, df, 'SELL')
        entry = df.iloc[40]['close']
        assert stop > entry  # стоп выше входа для SELL
    
    def test_get_target_buy(self):
        """Цель для BUY."""
        s = WyckoffBaseStrategy(target_atr_mult=2.0)
        df = make_df(50)
        analysis = WyckoffAnalysis()
        entry = df.iloc[40]['close']
        stop = entry - 0.001
        target = s._get_target(analysis, 40, df, 'BUY', entry, stop)
        assert target > entry
    
    def test_get_target_sell(self):
        """Цель для SELL."""
        s = WyckoffBaseStrategy(target_atr_mult=2.0)
        df = make_df(50)
        analysis = WyckoffAnalysis()
        entry = df.iloc[40]['close']
        stop = entry + 0.001
        target = s._get_target(analysis, 40, df, 'SELL', entry, stop)
        assert target < entry
    
    def test_should_enter_base_returns_none(self):
        """Базовая стратегия не входит."""
        s = WyckoffBaseStrategy()
        df = make_df(50)
        analysis = WyckoffAnalysis()
        result = s.should_enter(analysis, 40, df)
        assert result is None
    
    def test_generate_signals_empty_df(self):
        """Пустой df → пустой список."""
        s = WyckoffSpringStrategy()
        signals = s.generate_signals(None)
        assert signals == []
    
    def test_generate_signals_short_df(self):
        """Короткий df → пустой список."""
        s = WyckoffSpringStrategy()
        df = make_df(20)
        signals = s.generate_signals(df)
        assert signals == []
    
    def test_find_event_by_type(self):
        """Поиск события по типу."""
        s = WyckoffBaseStrategy()
        analysis = WyckoffAnalysis()
        analysis.events = [
            make_event('SC', idx=10),
            make_event('Spring', idx=20),
        ]
        result = s._find_event_by_type(analysis, 'Spring')
        assert result is not None
        assert result.type == 'Spring'
    
    def test_find_event_by_type_missing(self):
        """Событие не найдено."""
        s = WyckoffBaseStrategy()
        analysis = WyckoffAnalysis()
        analysis.events = [make_event('SC', idx=10)]
        result = s._find_event_by_type(analysis, 'Spring')
        assert result is None


class TestWyckoffSpringStrategy:
    def test_init(self):
        """Инициализация."""
        s = WyckoffSpringStrategy()
        assert 'Spring' in s.name
        assert s.target_atr_mult == 2.5
    
    def test_should_enter_no_phase(self):
        """Нет фазы → None."""
        s = WyckoffSpringStrategy()
        df = make_df(50)
        analysis = WyckoffAnalysis()
        # current_phase = None
        assert s.should_enter(analysis, 40, df) is None
    
    def test_should_enter_wrong_phase(self):
        """Distribution → None."""
        s = WyckoffSpringStrategy()
        df = make_df(50)
        analysis = make_analysis_with_phase(Phase.DISTRIBUTION, events=[
            make_event('Spring', idx=40)
        ])
        assert s.should_enter(analysis, 40, df) is None
    
    def test_should_enter_low_confidence(self):
        """Низкая confidence → None."""
        s = WyckoffSpringStrategy(min_confidence=0.7)
        df = make_df(50)
        analysis = make_analysis_with_phase(
            Phase.ACCUMULATION, confidence=0.4,
            events=[make_event('Spring', idx=40)],
        )
        assert s.should_enter(analysis, 40, df) is None
    
    def test_should_enter_no_spring(self):
        """Нет Spring → None."""
        s = WyckoffSpringStrategy()
        df = make_df(50)
        analysis = make_analysis_with_phase(Phase.ACCUMULATION, events=[])
        assert s.should_enter(analysis, 40, df) is None
    
    def test_should_enter_valid(self):
        """Валидный Spring → сигнал BUY."""
        s = WyckoffSpringStrategy(min_confidence=0.5)
        df = make_df(100)
        analysis = make_analysis_with_phase(
            Phase.ACCUMULATION, confidence=0.8,
            events=[make_event('Spring', idx=98)],
        )
        result = s.should_enter(analysis, 98, df)
        assert result is not None
        assert result['direction'] == 'BUY'
        assert result['pattern'] == 'Spring'


class TestWyckoffSOSStrategy:
    def test_init(self):
        """Инициализация."""
        s = WyckoffSOSStrategy()
        assert 'SOS' in s.name
    
    def test_should_enter_valid(self):
        """SOS в Accumulation → BUY."""
        s = WyckoffSOSStrategy(min_confidence=0.5)
        df = make_df(100)
        analysis = make_analysis_with_phase(
            Phase.ACCUMULATION, confidence=0.8,
            events=[make_event('SOS', idx=98, direction='bullish')],
        )
        result = s.should_enter(analysis, 98, df)
        assert result is not None
        assert result['direction'] == 'BUY'
        assert 'SOS' in result['pattern']
    
    def test_should_enter_markup(self):
        """SOS в Markup → BUY."""
        s = WyckoffSOSStrategy(min_confidence=0.5)
        df = make_df(100)
        analysis = make_analysis_with_phase(
            Phase.MARKUP, confidence=0.8,
            events=[make_event('SOS', idx=98)],
        )
        result = s.should_enter(analysis, 98, df)
        assert result is not None
    
    def test_should_enter_wrong_phase(self):
        """SOS в Distribution → None."""
        s = WyckoffSOSStrategy()
        df = make_df(100)
        analysis = make_analysis_with_phase(
            Phase.DISTRIBUTION, confidence=0.8,
            events=[make_event('SOS', idx=98)],
        )
        assert s.should_enter(analysis, 98, df) is None
    
    def test_with_lps_bonus(self):
        """SOS + LPS → pattern с '+LPS'."""
        s = WyckoffSOSStrategy(min_confidence=0.5)
        df = make_df(100)
        analysis = make_analysis_with_phase(
            Phase.ACCUMULATION, confidence=0.8,
            events=[
                make_event('SOS', idx=98),
                make_event('LPS', idx=95),
            ],
        )
        result = s.should_enter(analysis, 98, df)
        assert result is not None
        assert '+LPS' in result['pattern']


class TestWyckoffUTADStrategy:
    def test_init(self):
        """Инициализация."""
        s = WyckoffUTADStrategy()
        assert 'UT' in s.name
    
    def test_should_enter_valid(self):
        """UT в Distribution → SELL."""
        s = WyckoffUTADStrategy(min_confidence=0.5)
        df = make_df(100)
        analysis = make_analysis_with_phase(
            Phase.DISTRIBUTION, confidence=0.8,
            events=[make_event('UT', idx=98, direction='bearish')],
        )
        result = s.should_enter(analysis, 98, df)
        assert result is not None
        assert result['direction'] == 'SELL'
        assert result['pattern'] == 'UT'
    
    def test_should_enter_wrong_phase(self):
        """UT в Accumulation → None."""
        s = WyckoffUTADStrategy()
        df = make_df(100)
        analysis = make_analysis_with_phase(
            Phase.ACCUMULATION, confidence=0.8,
            events=[make_event('UT', idx=98)],
        )
        assert s.should_enter(analysis, 98, df) is None


class TestWyckoffSOWStrategy:
    def test_init(self):
        """Инициализация."""
        s = WyckoffSOWStrategy()
        assert 'SOW' in s.name
    
    def test_should_enter_valid(self):
        """SOW в Distribution → SELL."""
        s = WyckoffSOWStrategy(min_confidence=0.5)
        df = make_df(100)
        analysis = make_analysis_with_phase(
            Phase.DISTRIBUTION, confidence=0.8,
            events=[make_event('SOW', idx=98, direction='bearish')],
        )
        result = s.should_enter(analysis, 98, df)
        assert result is not None
        assert result['direction'] == 'SELL'
        assert 'SOW' in result['pattern']
    
    def test_should_enter_markdown(self):
        """SOW в Markdown → SELL."""
        s = WyckoffSOWStrategy(min_confidence=0.5)
        df = make_df(100)
        analysis = make_analysis_with_phase(
            Phase.MARKDOWN, confidence=0.8,
            events=[make_event('SOW', idx=98)],
        )
        result = s.should_enter(analysis, 98, df)
        assert result is not None


class TestWyckoffCombinedStrategy:
    def test_init(self):
        """Инициализация."""
        s = WyckoffCombinedStrategy()
        assert 'Combined' in s.name
    
    def test_spring_signal(self):
        """Spring → BUY."""
        s = WyckoffCombinedStrategy(min_confidence=0.4)
        df = make_df(100)
        analysis = make_analysis_with_phase(
            Phase.ACCUMULATION, confidence=0.8,
            events=[make_event('Spring', idx=98)],
        )
        result = s.should_enter(analysis, 98, df)
        assert result is not None
        assert result['direction'] == 'BUY'
    
    def test_ut_signal(self):
        """UT → SELL."""
        s = WyckoffCombinedStrategy(min_confidence=0.4)
        df = make_df(100)
        analysis = make_analysis_with_phase(
            Phase.DISTRIBUTION, confidence=0.8,
            events=[make_event('UT', idx=98, direction='bearish')],
        )
        result = s.should_enter(analysis, 98, df)
        assert result is not None
        assert result['direction'] == 'SELL'
    
    def test_no_signal_wrong_phase(self):
        """Нет сигнала вне Accumulation/Distribution."""
        s = WyckoffCombinedStrategy()
        df = make_df(100)
        analysis = make_analysis_with_phase(
            Phase.UNKNOWN, confidence=0.8,
            events=[make_event('Spring', idx=98)],
        )
        result = s.should_enter(analysis, 98, df)
        assert result is None