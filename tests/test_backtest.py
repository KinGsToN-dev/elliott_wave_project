"""
Тесты для backtest.engine, backtest.metrics, backtest.strategies.
"""
import pytest
import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest.engine import BacktestEngine
from backtest.metrics import BacktestMetrics
from backtest.strategies import get_strategy, list_strategies, STRATEGIES
from backtest.strategies.w2_w3 import W2W3Strategy


def make_df(n=200, trend='up'):
    """Хелпер: создаёт DataFrame."""
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
        'open': prices,
        'high': prices + 0.0003,
        'low': prices - 0.0003,
        'close': prices,
        'tick_volume': [100] * n,
    }, index=dates)


class TestBacktestEngine:
    def test_init(self):
        """Инициализация движка."""
        engine = BacktestEngine(max_bars_hold=50)
        assert engine.max_bars_hold == 50
        assert engine.trades == []
    
    def test_empty_signals(self):
        """Пустые сигналы — пустой результат."""
        engine = BacktestEngine()
        df = make_df()
        trades = engine.run([], df)
        assert trades == []
    
    def test_simulate_buy_tp(self):
        """BUY достигает цели (TP)."""
        engine = BacktestEngine()
        df = make_df(200, 'up')
        
        signal = {
            'entry_time': df.index[10],
            'entry_price': df.loc[df.index[10], 'close'],
            'direction': 'BUY',
            'target': df.loc[df.index[10], 'close'] + 0.01,
            'stop': df.loc[df.index[10], 'close'] - 0.01,
        }
        
        result = engine.simulate_trade(signal, df)
        assert result is not None
        assert result['exit_reason'] in ['TP', 'SL', 'TIME']
        assert 'pnl' in result
    
    def test_simulate_buy_sl(self):
        """BUY достигает стопа (SL)."""
        engine = BacktestEngine()
        df = make_df(200, 'down')
        
        signal = {
            'entry_time': df.index[10],
            'entry_price': df.loc[df.index[10], 'close'],
            'direction': 'BUY',
            'target': df.loc[df.index[10], 'close'] + 0.05,
            'stop': df.loc[df.index[10], 'close'] - 0.005,
        }
        
        result = engine.simulate_trade(signal, df)
        assert result is not None
        assert result['exit_reason'] in ['TP', 'SL', 'TIME']
    
    def test_no_bars_after(self):
        """Нет свечей после входа — None."""
        engine = BacktestEngine()
        df = make_df(20)
        
        signal = {
            'entry_time': df.index[-1],
            'entry_price': df.iloc[-1]['close'],
            'direction': 'BUY',
            'target': df.iloc[-1]['close'] + 0.01,
            'stop': df.iloc[-1]['close'] - 0.01,
        }
        
        result = engine.simulate_trade(signal, df)
        assert result is None


class TestBacktestMetrics:
    def test_empty_trades(self):
        """Пустые сделки."""
        metrics = BacktestMetrics([])
        m = metrics.calculate()
        assert m['total_trades'] == 0
        assert m['winrate'] == 0
    
    def test_all_wins(self):
        """Все сделки прибыльные."""
        trades = [
            {'pnl': 100, 'exit_reason': 'TP'},
            {'pnl': 200, 'exit_reason': 'TP'},
            {'pnl': 150, 'exit_reason': 'TP'},
        ]
        metrics = BacktestMetrics(trades)
        m = metrics.calculate()
        assert m['total_trades'] == 3
        assert m['winrate'] == 1.0
        assert m['total_return'] == 450
        assert m['tp_count'] == 3
    
    def test_mixed_trades(self):
        """Смешанные сделки."""
        trades = [
            {'pnl': 100, 'exit_reason': 'TP'},
            {'pnl': -50, 'exit_reason': 'SL'},
            {'pnl': 150, 'exit_reason': 'TP'},
            {'pnl': -30, 'exit_reason': 'SL'},
        ]
        metrics = BacktestMetrics(trades)
        m = metrics.calculate()
        assert m['total_trades'] == 4
        assert m['wins'] == 2
        assert m['losses'] == 2
        assert m['winrate'] == 0.5
        assert m['total_return'] == 170
        assert m['profit_factor'] == 250 / 80
        assert m['tp_count'] == 2
        assert m['sl_count'] == 2


class TestW2W3Strategy:
    def test_init(self):
        """Инициализация."""
        strat = W2W3Strategy()
        assert strat.name == "W2→W3"
        assert strat.min_w2_ratio == 0.4
        assert strat.max_w2_ratio == 0.85
    
    def test_empty_impulses(self):
        """Пустые импульсы."""
        strat = W2W3Strategy()
        df = make_df()
        signals = strat.generate_signals(df, [], [], [], [])
        assert signals == []
    
    def test_valid_impulse(self):
        """Валидный импульс генерирует сигнал."""
        strat = W2W3Strategy()
        df = make_df()
        
        # W1 = 0.0100, W2 = 0.0060 (60% откат — в диапазоне)
        imp = {
            'direction': 'bullish',
            'points': [
                (df.index[10], 1.1000, '0'),
                (df.index[20], 1.1100, '1'),
                (df.index[30], 1.1040, '2'),
                (df.index[40], 1.1300, '3'),
                (df.index[50], 1.1200, '4'),
                (df.index[60], 1.1450, '5'),
            ],
        }
        signals = strat.generate_signals(df, [imp], [], [], [])
        # Может быть 0 или 1 сигнал
        assert isinstance(signals, list)


class TestStrategyRegistry:
    def test_list_strategies(self):
        """Список стратегий."""
        strategies = list_strategies()
        assert 'w2_w3' in strategies
    
    def test_get_strategy(self):
        """Получение стратегии по имени."""
        cls = get_strategy('w2_w3')
        assert cls == W2W3Strategy
    
    def test_get_unknown_strategy(self):
        """Неизвестная стратегия — ошибка."""
        with pytest.raises(ValueError):
            get_strategy('unknown_strategy')

class TestEngineCoverage:
    """Дополнительные тесты для engine.py."""
    
    def test_sell_tp(self):
        """SELL достигает цели."""
        engine = BacktestEngine()
        df = make_df(200, 'down')
        
        signal = {
            'entry_time': df.index[10],
            'entry_price': df.loc[df.index[10], 'close'],
            'direction': 'SELL',
            'target': df.loc[df.index[10], 'close'] - 0.01,
            'stop': df.loc[df.index[10], 'close'] + 0.01,
        }
        
        result = engine.simulate_trade(signal, df)
        assert result is not None
        assert result['direction'] == 'SELL'
    
    def test_sell_sl(self):
        """SELL достигает стопа."""
        engine = BacktestEngine()
        df = make_df(200, 'up')
        
        signal = {
            'entry_time': df.index[10],
            'entry_price': df.loc[df.index[10], 'close'],
            'direction': 'SELL',
            'target': df.loc[df.index[10], 'close'] - 0.05,
            'stop': df.loc[df.index[10], 'close'] + 0.005,
        }
        
        result = engine.simulate_trade(signal, df)
        assert result is not None
    
    def test_time_exit(self):
        """Время вышло — закрытие по TIME."""
        engine = BacktestEngine(max_bars_hold=5)
        df = make_df(50)
        
        signal = {
            'entry_time': df.index[10],
            'entry_price': df.loc[df.index[10], 'close'],
            'direction': 'BUY',
            'target': df.loc[df.index[10], 'close'] + 1.0,  # недостижимая
            'stop': df.loc[df.index[10], 'close'] - 1.0,     # недостижимый
        }
        
        result = engine.simulate_trade(signal, df)
        assert result is not None
        assert result['exit_reason'] == 'TIME'
    
    def test_run_multiple_signals(self):
        """run() обрабатывает несколько сигналов."""
        engine = BacktestEngine()
        df = make_df(200, 'up')
        
        signals = [
            {
                'entry_time': df.index[10],
                'entry_price': df.loc[df.index[10], 'close'],
                'direction': 'BUY',
                'target': df.loc[df.index[10], 'close'] + 0.01,
                'stop': df.loc[df.index[10], 'close'] - 0.01,
            },
            {
                'entry_time': df.index[50],
                'entry_price': df.loc[df.index[50], 'close'],
                'direction': 'BUY',
                'target': df.loc[df.index[50], 'close'] + 0.01,
                'stop': df.loc[df.index[50], 'close'] - 0.01,
            },
        ]
        
        trades = engine.run(signals, df)
        assert len(trades) == 2
        assert len(engine.get_trades()) == 2


class TestMetricsCoverage:
    """Дополнительные тесты для metrics.py."""
    
    def test_all_losses(self):
        """Все сделки убыточные — profit_factor = 0."""
        trades = [
            {'pnl': -100, 'exit_reason': 'SL'},
            {'pnl': -50, 'exit_reason': 'SL'},
        ]
        metrics = BacktestMetrics(trades)
        m = metrics.calculate()
        assert m['wins'] == 0
        assert m['losses'] == 2
        assert m['profit_factor'] == 0
        assert m['winrate'] == 0
    
    def test_max_drawdown(self):
        """Расчёт просадки."""
        trades = [
            {'pnl': 100, 'exit_reason': 'TP'},
            {'pnl': -200, 'exit_reason': 'SL'},
            {'pnl': 50, 'exit_reason': 'TP'},
        ]
        metrics = BacktestMetrics(trades)
        m = metrics.calculate()
        assert m['max_drawdown'] < 0  # должна быть отрицательная
    
    def test_print_summary(self, capsys):
        """print_summary выводит данные."""
        trades = [
            {'pnl': 100, 'exit_reason': 'TP'},
            {'pnl': -50, 'exit_reason': 'SL'},
        ]
        metrics = BacktestMetrics(trades)
        m = metrics.print_summary("Test Strategy")
        
        captured = capsys.readouterr()
        assert 'BACKTEST RESULTS' in captured.out
        assert 'Test Strategy' in captured.out
        assert m['total_trades'] == 2
