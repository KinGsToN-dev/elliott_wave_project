"""
Тесты для live.runner и live.runner_multi.

Используют моки, чтобы не дёргать MT5 и Telegram.
"""
import pytest
import sys
import os
from datetime import datetime
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from live.runner import LiveRunner
from live.runner_multi import MultiLiveRunner


class TestLiveRunner:
    def test_init(self, mocker):
        """LiveRunner создаёт monitor, notifier, journal."""
        # Мокаем TelegramNotifier, чтобы не читать config
        mocker.patch('live.runner.TelegramNotifier')
        mocker.patch('live.runner.SignalJournal')
        
        runner = LiveRunner(symbol='EURUSD', mode='swing')
        
        assert runner.monitor is not None
        assert runner.monitor.symbol == 'EURUSD'
        assert runner.monitor.mode_name == 'swing'
        assert runner.notifier is not None
        assert runner.journal is not None
    
    def test_run_no_signals(self, mocker):
        """run() без сигналов не падает."""
        mocker.patch('live.runner.TelegramNotifier')
        mocker.patch('live.runner.SignalJournal')
        
        runner = LiveRunner(symbol='EURUSD', mode='swing')
        
        # Мокаем monitor.run — возвращает пустой генератор
        def empty_gen(max_iterations=None):
            return
            yield  # делает функцию генератором
        
        mocker.patch.object(runner.monitor, 'run', side_effect=empty_gen)
        
        # Должно завершиться без ошибок
        runner.run(max_iterations=1)
        assert True
    
    def test_run_with_signals(self, mocker):
        """run() отправляет сигналы в Telegram и журнал."""
        mock_notifier_cls = mocker.patch('live.runner.TelegramNotifier')
        mock_journal_cls = mocker.patch('live.runner.SignalJournal')
        
        mock_notifier = MagicMock()
        mock_notifier.notify_signals.return_value = 1
        mock_notifier_cls.return_value = mock_notifier
        
        mock_journal = MagicMock()
        mock_journal.add_many.return_value = 1
        mock_journal_cls.return_value = mock_journal
        
        runner = LiveRunner(symbol='EURUSD', mode='swing')
        
        test_signal = {
            'symbol': 'EURUSD', 'mode': 'swing', 'strategy': 'w2_w3',
            'direction': 'BUY', 'entry_price': 1.1000, 'target': 1.1100,
            'stop': 1.0950, 'pattern': 'W2_completion',
        }
        
        def signal_gen(max_iterations=None):
            yield [test_signal]
        
        mocker.patch.object(runner.monitor, 'run', side_effect=signal_gen)
        
        runner.run(max_iterations=1)
        
        # Проверяем, что notifier и journal вызывались
        mock_notifier.notify_signals.assert_called_once()
        mock_journal.add_many.assert_called_once()


class TestMultiLiveRunner:
    def test_init_single_symbol(self, mocker):
        """MultiLiveRunner с одним символом."""
        mocker.patch('live.runner_multi.TelegramNotifier')
        mocker.patch('live.runner_multi.SignalJournal')
        mocker.patch('live.runner_multi.SignalState')
        mocker.patch('live.runner_multi.TelegramBot')
        
        runner = MultiLiveRunner(symbols=['EURUSD'], modes=['swing'])
        
        assert len(runner.monitors) == 1
        assert runner.symbols == ['EURUSD']
        assert runner.modes == ['swing']
    
    def test_init_multiple_combinations(self, mocker):
        """MultiLiveRunner с несколькими символами и режимами."""
        mocker.patch('live.runner_multi.TelegramNotifier')
        mocker.patch('live.runner_multi.SignalJournal')
        mocker.patch('live.runner_multi.SignalState')
        mocker.patch('live.runner_multi.TelegramBot')
        
        runner = MultiLiveRunner(
            symbols=['EURUSD', 'GBPUSD'],
            modes=['swing', 'intraday'],
        )
        
        # 2 символа × 2 режима = 4 монитора
        assert len(runner.monitors) == 4
    
    def test_bot_thread_starts(self, mocker):
        """_bot_thread запускает TelegramBot.run()."""
        mocker.patch('live.runner_multi.TelegramNotifier')
        mocker.patch('live.runner_multi.SignalJournal')
        mocker.patch('live.runner_multi.SignalState')
        mock_bot_cls = mocker.patch('live.runner_multi.TelegramBot')
        
        mock_bot = MagicMock()
        mock_bot_cls.return_value = mock_bot
        
        runner = MultiLiveRunner(symbols=['EURUSD'], modes=['swing'])
        
        runner._bot_thread()
        
        mock_bot.run.assert_called_once()