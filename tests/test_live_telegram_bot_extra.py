"""
Дополнительные тесты для live.telegram_bot.

Покрывают: /stop, /history, /help с новыми командами.
"""
import pytest
import sys
import os
import csv
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from live.telegram_bot import TelegramBot


@pytest.fixture
def bot(mocker):
    """Создаёт TelegramBot с моками."""
    mock_notifier_cls = mocker.patch('live.telegram_bot.TelegramNotifier')
    mock_notifier = MagicMock()
    mock_notifier.bot_token = 'TEST_TOKEN'
    mock_notifier.chat_id = '123456'
    mock_notifier.send_message.return_value = True
    mock_notifier_cls.return_value = mock_notifier
    
    mock_state_cls = mocker.patch('live.telegram_bot.SignalState')
    mock_state = MagicMock()
    mock_state.get_active.return_value = []
    mock_state.get_stats.return_value = {
        'total': 0, 'active': 0, 'target_hit': 0,
        'stop_hit': 0, 'winrate': 0.0,
    }
    mock_state.state = {}
    mock_state_cls.return_value = mock_state
    
    return TelegramBot()


class TestStopCommand:
    def test_stop_sets_running_false(self, bot):
        """Команда /stop выставляет running = False."""
        bot.running = True
        response = bot.handle_command('/stop')
        assert bot.running is False
        assert response is not None
        assert 'остановлен' in response.lower()

    def test_stop_returns_signal_count(self, bot):
        """Команда /stop показывает количество сигналов."""
        bot.state.state = {'sig1': {}, 'sig2': {}, 'sig3': {}}
        response = bot.handle_command('/stop')
        assert '3' in response

    def test_stop_case_insensitive(self, bot):
        """Команда /STOP работает."""
        bot.running = True
        response = bot.handle_command('/STOP')
        assert bot.running is False
        assert response is not None


class TestHistoryCommand:
    def test_history_no_file(self, bot, mocker):
        """История без файла — сообщение 'пуста'."""
        mocker.patch('os.path.exists', return_value=False)
        response = bot.handle_command('/history')
        assert response is not None
        assert 'пуста' in response.lower() or 'история' in response.lower()

    def test_history_with_data(self, bot, mocker, tmp_path):
        """История с данными — форматируется."""
        # Создаём фейковый CSV
        today = __import__('datetime').datetime.now().strftime('%Y%m%d')
        log_dir = tmp_path / 'logs'
        log_dir.mkdir()
        csv_file = log_dir / f'signals_{today}.csv'
        
        with open(csv_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'timestamp', 'symbol', 'mode', 'strategy', 'pattern',
                'direction', 'entry_price', 'target', 'stop', 'r_r'
            ])
            writer.writeheader()
            writer.writerow({
                'timestamp': '2026-10-11 10:00:00',
                'symbol': 'EURUSD', 'mode': 'swing', 'strategy': 'w2_w3',
                'pattern': 'W2', 'direction': 'BUY',
                'entry_price': '1.10000', 'target': '1.11000',
                'stop': '1.09500', 'r_r': '2.00',
            })
            writer.writerow({
                'timestamp': '2026-10-11 11:00:00',
                'symbol': 'GBPUSD', 'mode': 'intraday', 'strategy': 'w4_w5',
                'pattern': 'W4', 'direction': 'SELL',
                'entry_price': '1.30000', 'target': '1.29000',
                'stop': '1.30500', 'r_r': '2.00',
            })
        
        # Мокаем путь к файлу
        mocker.patch(
            'live.telegram_bot.os.path.dirname',
            return_value=str(tmp_path.parent),
        )
        mocker.patch('os.path.exists', return_value=True)
        
        # Проще: подменяем filepath напрямую через mock
        original_open = open
        def mock_open(path, *args, **kwargs):
            if 'signals_' in str(path):
                return original_open(csv_file, *args, **kwargs)
            return original_open(path, *args, **kwargs)
        
        mocker.patch('builtins.open', side_effect=mock_open)
        mocker.patch('os.path.join', return_value=str(csv_file))
        mocker.patch('live.telegram_bot.os.path.abspath', return_value=str(csv_file))
        mocker.patch('live.telegram_bot.os.path.dirname', return_value=str(tmp_path))
        
        response = bot._read_history(n=10)
        assert 'EURUSD' in response or 'GBPUSD' in response

    def test_history_with_n_parameter(self, bot, mocker):
        """История с параметром /history 5."""
        mocker.patch.object(bot, '_read_history', return_value="📜 История")
        response = bot.handle_command('/history 5')
        bot._read_history.assert_called_once_with(5)

    def test_history_default_n(self, bot, mocker):
        """История без параметра — n=10 по умолчанию."""
        mocker.patch.object(bot, '_read_history', return_value="📜 История")
        response = bot.handle_command('/history')
        bot._read_history.assert_called_once_with(10)

    def test_history_invalid_n(self, bot, mocker):
        """История с невалидным N — используется 10."""
        mocker.patch.object(bot, '_read_history', return_value="📜 История")
        response = bot.handle_command('/history abc')
        bot._read_history.assert_called_once_with(10)

    def test_history_empty_journal(self, bot, mocker, tmp_path):
        """Пустой CSV — сообщение 'пуста'."""
        today = __import__('datetime').datetime.now().strftime('%Y%m%d')
        log_dir = tmp_path / 'logs'
        log_dir.mkdir()
        csv_file = log_dir / f'signals_{today}.csv'
        
        with open(csv_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'timestamp', 'symbol', 'mode', 'strategy', 'pattern',
                'direction', 'entry_price', 'target', 'stop', 'r_r'
            ])
            writer.writeheader()
        
        mocker.patch('os.path.exists', return_value=True)
        mocker.patch('os.path.join', return_value=str(csv_file))
        mocker.patch('live.telegram_bot.os.path.abspath', return_value=str(csv_file))
        mocker.patch('live.telegram_bot.os.path.dirname', return_value=str(tmp_path))
        
        response = bot._read_history(n=10)
        assert 'пуста' in response.lower()


class TestStartHelpUpdated:
    def test_start_mentions_stop(self, bot):
        """ /start упоминает /stop."""
        response = bot.handle_command('/start')
        assert '/stop' in response

    def test_start_mentions_history(self, bot):
        """/start упоминает /history."""
        response = bot.handle_command('/start')
        assert '/history' in response

    def test_help_mentions_stop(self, bot):
        """/help упоминает /stop."""
        response = bot.handle_command('/help')
        assert '/stop' in response

    def test_help_mentions_history(self, bot):
        """/help упоминает /history."""
        response = bot.handle_command('/help')
        assert '/history' in response