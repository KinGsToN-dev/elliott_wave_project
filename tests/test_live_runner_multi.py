"""
Тесты для live.runner_multi (расширенные).

Покрывают: run, _bot_thread, обработка ошибок.
"""
import pytest
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from live.runner_multi import MultiLiveRunner


class TestRunLoop:
    def test_run_handles_keyboard_interrupt(self, mocker):
        """run ловит KeyboardInterrupt."""
        mocker.patch('live.runner_multi.TelegramNotifier')
        mocker.patch('live.runner_multi.SignalJournal')
        mocker.patch('live.runner_multi.SignalState')
        mocker.patch('live.runner_multi.TelegramBot')
        mocker.patch('live.runner_multi.time.sleep', side_effect=KeyboardInterrupt)
        mocker.patch('live.runner_multi.threading.Thread')
        
        runner = MultiLiveRunner(symbols=['EURUSD'], modes=['swing'])
        
        # Мокаем run_once у монитора
        for m in runner.monitors:
            mocker.patch.object(m, 'run_once', return_value=[])
        
        # Должно завершиться без ошибок
        runner.run()
        assert True

    def test_run_with_signals(self, mocker):
        """run обрабатывает сигналы от мониторов."""
        mock_notifier_cls = mocker.patch('live.runner_multi.TelegramNotifier')
        mock_notifier = MagicMock()
        mock_notifier_cls.return_value = mock_notifier
        
        mock_journal_cls = mocker.patch('live.runner_multi.SignalJournal')
        mock_journal = MagicMock()
        mock_journal_cls.return_value = mock_journal
        
        mock_state_cls = mocker.patch('live.runner_multi.SignalState')
        mock_state = MagicMock()
        mock_state_cls.return_value = mock_state
        
        mocker.patch('live.runner_multi.TelegramBot')
        mocker.patch('live.runner_multi.threading.Thread')
        
        # Останавливаем цикл после 1 итерации
        mocker.patch('live.runner_multi.time.sleep', side_effect=KeyboardInterrupt)
        
        runner = MultiLiveRunner(symbols=['EURUSD'], modes=['swing'])
        
        test_signal = {
            'symbol': 'EURUSD', 'mode': 'swing', 'strategy': 'w2_w3',
            'direction': 'BUY', 'entry_price': 1.1000, 'target': 1.1100,
            'stop': 1.0950, 'pattern': 'W2',
        }
        for m in runner.monitors:
            mocker.patch.object(m, 'run_once', return_value=[test_signal])
        
        runner.run()
        
        # notifier и journal должны были вызваться
        mock_notifier.notify_signals.assert_called()
        mock_journal.add_many.assert_called()


class TestInitErrors:
    def test_init_handles_bad_mode(self, mocker):
        """MultiLiveRunner не падает при неверном режиме."""
        mocker.patch('live.runner_multi.TelegramNotifier')
        mocker.patch('live.runner_multi.SignalJournal')
        mocker.patch('live.runner_multi.SignalState')
        mocker.patch('live.runner_multi.TelegramBot')
        
        # Один режим невалидный — monitor не создастся
        # (get_mode бросит исключение)
        mocker.patch(
            'live.runner_multi.MarketMonitor',
            side_effect=Exception('Bad mode'),
        )
        
        runner = MultiLiveRunner(symbols=['EURUSD'], modes=['invalid'])
        
        # Мониторов 0, но runner создан
        assert len(runner.monitors) == 0