"""
Тесты для live.monitor (расширенные).

Покрывают run_once, generate_signals, load_data с моками MT5.
"""
import pytest
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from live.monitor import MarketMonitor
from live.state import SignalState


def make_df(n=100):
    """DataFrame с индексом вокруг текущего времени."""
    start = datetime.now() - timedelta(hours=n)
    np.random.seed(42)
    dates = [start + timedelta(hours=i) for i in range(n)]
    prices = [1.1000 + np.random.randn() * 0.001 for _ in range(n)]
    return pd.DataFrame({
        'open': prices,
        'high': [p + 0.0005 for p in prices],
        'low': [p - 0.0005 for p in prices],
        'close': prices,
        'tick_volume': [100] * n,
    }, index=dates)


class TestLoadData:
    def test_load_data_no_mt5(self, mocker):
        """load_data возвращает None без MT5."""
        mocker.patch('live.monitor.MT5_AVAILABLE', False)
        monitor = MarketMonitor(symbol='EURUSD', mode='swing')
        assert monitor.load_data() is None

    def test_load_data_mt5_connect_fail(self, mocker):
        """load_data возвращает None если connect fail."""
        mocker.patch('live.monitor.MT5_AVAILABLE', True)
        mock_connector_cls = mocker.patch('live.monitor.MT5Connector')
        mock_connector = MagicMock()
        mock_connector.connect.return_value = False
        mock_connector_cls.return_value = mock_connector
        
        monitor = MarketMonitor(symbol='EURUSD', mode='swing')
        assert monitor.load_data() is None

    def test_load_data_success(self, mocker):
        """load_data возвращает DataFrame."""
        mocker.patch('live.monitor.MT5_AVAILABLE', True)
        mock_connector_cls = mocker.patch('live.monitor.MT5Connector')
        mock_connector = MagicMock()
        mock_connector.connect.return_value = True
        mock_connector.get_candles.return_value = make_df(50)
        mock_connector_cls.return_value = mock_connector
        
        monitor = MarketMonitor(symbol='EURUSD', mode='swing')
        df = monitor.load_data()
        
        assert df is not None
        assert len(df) == 50
        mock_connector.disconnect.assert_called_once()


class TestGenerateSignals:
    def test_no_strategies(self, mocker):
        """generate_signals с пустым списком стратегий."""
        monitor = MarketMonitor(symbol='EURUSD', mode='swing', strategies=[])
        df = make_df(50)
        signals = monitor.generate_signals(df, [], [], [])
        assert signals == []

    def test_strategy_exception_handled(self, mocker):
        """generate_signals ловит исключения стратегий."""
        monitor = MarketMonitor(symbol='EURUSD', mode='swing', strategies=['combined'])
        df = make_df(50)
        
        # Мокаем get_strategy, чтобы он бросал исключение
        mock_strategy_cls = MagicMock(side_effect=Exception('Test error'))
        mocker.patch('live.monitor.get_strategy', return_value=mock_strategy_cls)
        
        # Не должно упасть
        signals = monitor.generate_signals(df, [], [], [])
        assert signals == []


class TestRunOnce:
    def test_run_once_no_data(self, mocker):
        """run_once возвращает [] без данных."""
        mocker.patch.object(MarketMonitor, 'load_data', return_value=None)
        monitor = MarketMonitor(symbol='EURUSD', mode='swing')
        monitor.state.state = {}
        monitor.state._save()
        
        result = monitor.run_once()
        assert result == []

    def test_run_once_short_data(self, mocker):
        """run_once возвращает [] при < 20 барах."""
        mocker.patch.object(MarketMonitor, 'load_data', return_value=make_df(10))
        monitor = MarketMonitor(symbol='EURUSD', mode='swing')
        monitor.state.state = {}
        monitor.state._save()
        
        result = monitor.run_once()
        assert result == []

    def test_run_once_full_pipeline(self, mocker):
        """run_once проходит полный пайплайн."""
        df = make_df(50)
        mocker.patch.object(MarketMonitor, 'load_data', return_value=df)
        mocker.patch.object(MarketMonitor, 'analyze', return_value=([], [], [], []))
        mocker.patch.object(MarketMonitor, 'generate_signals', return_value=[])
        
        monitor = MarketMonitor(symbol='EURUSD', mode='swing')
        monitor.state.state = {}
        monitor.state._save()
        
        result = monitor.run_once()
        assert result == []

    def test_run_once_with_new_signal(self, mocker):
        """run_once добавляет новый сигнал в state."""
        df = make_df(50)
        mocker.patch.object(MarketMonitor, 'load_data', return_value=df)
        mocker.patch.object(MarketMonitor, 'analyze', return_value=([], [], [], []))
        
        # Возвращаем сигнал
        test_signal = {
            'symbol': 'EURUSD', 'mode': 'swing', 'strategy': 'w2_w3',
            'direction': 'BUY', 'entry_price': 1.1000, 'target': 1.1100,
            'stop': 1.0950, 'entry_time': datetime.now() - timedelta(hours=1),
            'pattern': 'W2',
        }
        mocker.patch.object(MarketMonitor, 'generate_signals', return_value=[test_signal])
        mocker.patch.object(MarketMonitor, 'is_signal_actual', return_value=True)
        
        monitor = MarketMonitor(symbol='EURUSD', mode='swing')
        monitor.state.state = {}
        monitor.state._save()
        
        result = monitor.run_once()
        
        assert len(result) == 1
        assert result[0]['symbol'] == 'EURUSD'

    def test_run_once_first_run_limits_to_3(self, mocker):
        """Первый запуск ограничивает 3 сигналами."""
        df = make_df(50)
        mocker.patch.object(MarketMonitor, 'load_data', return_value=df)
        mocker.patch.object(MarketMonitor, 'analyze', return_value=([], [], [], []))
        
        # 10 сигналов
        test_signals = [
            {
                'symbol': 'EURUSD', 'mode': 'swing', 'strategy': 'w2_w3',
                'direction': 'BUY', 'entry_price': 1.1000, 'target': 1.1100,
                'stop': 1.0950, 'entry_time': datetime.now() - timedelta(hours=1),
                'pattern': 'W2',
            }
            for _ in range(10)
        ]
        mocker.patch.object(MarketMonitor, 'generate_signals', return_value=test_signals)
        mocker.patch.object(MarketMonitor, 'is_signal_actual', return_value=True)
        
        monitor = MarketMonitor(symbol='EURUSD', mode='swing')
        monitor.state.state = {}
        monitor.state._save()
        
        result = monitor.run_once()
        
        # Первый запуск — только 3 последних
        assert len(result) == 3


class TestUpdateActiveSignals:
    def test_no_active_signals(self, mocker):
        """Нет активных — возвращает 0."""
        monitor = MarketMonitor(symbol='EURUSD', mode='swing')
        monitor.state.state = {}
        monitor.state._save()
        
        result = monitor.update_active_signals(make_df(50))
        assert result == 0

    def test_signal_not_in_df_range(self, mocker):
        """Сигнал, чей created_at позже df — не обновляется."""
        monitor = MarketMonitor(symbol='EURUSD', mode='swing')
        monitor.state.state = {}
        monitor.state._save()
        
        # Сигнал с created_at в будущем
        signal = {
            'symbol': 'EURUSD', 'mode': 'swing', 'strategy': 'w2_w3',
            'direction': 'BUY', 'entry_price': 1.1000, 'target': 1.1100,
            'stop': 1.0950, 'entry_time': datetime.now() - timedelta(hours=1),
        }
        sid = monitor.state.add(signal)
        monitor.state.state[sid]['created_at'] = (datetime.now() + timedelta(hours=100)).isoformat()
        monitor.state._save()
        
        # df не покрывает created_at
        result = monitor.update_active_signals(make_df(50))
        assert result == 0


class TestIsNewSignal:
    def test_new_signal(self):
        """Новый сигнал — True."""
        monitor = MarketMonitor(symbol='EURUSD', mode='swing')
        monitor.state.state = {}
        monitor.state._save()
        
        sig = {
            'symbol': 'EURUSD', 'mode': 'swing', 'strategy': 'w2_w3',
            'entry_time': datetime(2026, 1, 1),
        }
        assert monitor.is_new_signal(sig) is True

    def test_existing_signal(self):
        """Существующий сигнал — False."""
        monitor = MarketMonitor(symbol='EURUSD', mode='swing')
        monitor.state.state = {}
        monitor.state._save()
        
        sig = {
            'symbol': 'EURUSD', 'mode': 'swing', 'strategy': 'w2_w3',
            'direction': 'BUY', 'entry_price': 1.1000, 'target': 1.1100,
            'stop': 1.0950, 'entry_time': datetime(2026, 1, 1),
        }
        monitor.state.add(sig)
        assert monitor.is_new_signal(sig) is False


class TestIsSignalActual:
    def test_missing_fields(self):
        """Недостаточно полей — True (считаем актуальным)."""
        monitor = MarketMonitor(symbol='EURUSD', mode='swing')
        sig = {}
        assert monitor.is_signal_actual(sig, make_df(50)) is True

    def test_target_reached(self):
        """Цель достигнута — False (не актуален)."""
        monitor = MarketMonitor(symbol='EURUSD', mode='swing')
        df = make_df(100)
        
        sig = {
            'entry_time': datetime.now() - timedelta(hours=50),
            'target': 1.1100,
            'stop': 1.0950,
            'direction': 'BUY',
        }
        # Устанавливаем high выше target на баре после entry_time
        df.iloc[60, df.columns.get_loc('high')] = 1.1150
        
        assert monitor.is_signal_actual(sig, df) is False

    def test_stop_reached(self):
        """Стоп достигнут — False."""
        monitor = MarketMonitor(symbol='EURUSD', mode='swing')
        df = make_df(100)
        
        sig = {
            'entry_time': datetime.now() - timedelta(hours=50),
            'target': 1.1100,
            'stop': 1.0950,
            'direction': 'BUY',
        }
        df.iloc[60, df.columns.get_loc('low')] = 1.0900
        
        assert monitor.is_signal_actual(sig, df) is False

    def test_neither_reached(self):
        """Ни цель, ни стоп — True."""
        monitor = MarketMonitor(symbol='EURUSD', mode='swing')
        df = make_df(100)
        
        # Убираем все бары после entry_time
        sig = {
            'entry_time': datetime.now() + timedelta(hours=100),
            'target': 1.1100,
            'stop': 1.0950,
            'direction': 'BUY',
        }
        
        assert monitor.is_signal_actual(sig, df) is True