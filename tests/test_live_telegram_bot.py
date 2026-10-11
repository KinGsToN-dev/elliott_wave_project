"""
Тесты для live.telegram_bot.

Мокают requests, чтобы не отправлять реальные сообщения.
"""
import pytest
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from live.telegram_bot import TelegramBot


@pytest.fixture
def bot(mocker):
    """Создаёт TelegramBot с моками."""
    # Мокаем TelegramNotifier, чтобы не читать config
    mock_notifier_cls = mocker.patch('live.telegram_bot.TelegramNotifier')
    mock_notifier = MagicMock()
    mock_notifier.bot_token = 'TEST_TOKEN'
    mock_notifier.chat_id = '123456'
    mock_notifier.send_message.return_value = True
    mock_notifier_cls.return_value = mock_notifier
    
    # Мокаем SignalState
    mock_state_cls = mocker.patch('live.telegram_bot.SignalState')
    mock_state = MagicMock()
    mock_state.get_active.return_value = []
    mock_state.get_stats.return_value = {
        'total': 0, 'active': 0, 'target_hit': 0,
        'stop_hit': 0, 'winrate': 0.0,
    }
    mock_state_cls.return_value = mock_state
    
    return TelegramBot()


class TestHandleCommand:
    def test_start(self, bot):
        """Команда /start."""
        response = bot.handle_command('/start')
        assert response is not None
        assert 'Elliott Wave Bot' in response
        assert '/status' in response

    def test_help(self, bot):
        """Команда /help."""
        response = bot.handle_command('/help')
        assert response is not None
        assert 'Команды' in response

    def test_status(self, bot):
        """Команда /status."""
        response = bot.handle_command('/status')
        assert response is not None
        assert 'Статус' in response
        assert 'Активных' in response

    def test_signals_empty(self, bot):
        """Команда /signals без активных."""
        bot.state.get_active.return_value = []
        response = bot.handle_command('/signals')
        assert 'Нет актуальных' in response

    def test_signals_with_data(self, bot):
        """Команда /signals с активными."""
        bot.state.get_active.return_value = [
            {
                'symbol': 'EURUSD', 'mode': 'swing', 'strategy': 'w2_w3',
                'direction': 'BUY', 'entry_price': 1.1000, 'target': 1.1100,
                'r_r': 2.0, 'pips_target': 100,
            },
        ]
        response = bot.handle_command('/signals')
        assert 'EURUSD' in response
        assert 'Актуальные сигналы' in response

    def test_signals_swing(self, bot):
        """Команда /signals_swing."""
        bot.state.get_active.return_value = []
        response = bot.handle_command('/signals_swing')
        assert 'Swing' in response

    def test_signals_intraday(self, bot):
        """Команда /signals_intraday."""
        bot.state.get_active.return_value = []
        response = bot.handle_command('/signals_intraday')
        assert 'Intraday' in response

    def test_signals_scalping(self, bot):
        """Команда /signals_scalping."""
        bot.state.get_active.return_value = []
        response = bot.handle_command('/signals_scalping')
        assert 'Scalping' in response

    def test_stats(self, bot):
        """Команда /stats."""
        response = bot.handle_command('/stats')
        assert 'Статистика' in response

    def test_unknown_command(self, bot):
        """Неизвестная команда — None."""
        response = bot.handle_command('/unknown_command_xyz')
        assert response is None

    def test_case_insensitive(self, bot):
        """Команды не чувствительны к регистру."""
        r1 = bot.handle_command('/STATUS')
        r2 = bot.handle_command('/status')
        assert r1 == r2

    def test_with_whitespace(self, bot):
        """Команды с пробелами обрабатываются."""
        response = bot.handle_command('  /status  ')
        assert 'Статус' in response


class TestGetUpdates:
    def test_get_updates_success(self, bot, mocker):
        """get_updates возвращает результат при 200."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': [
                {'update_id': 1, 'message': {'text': '/status'}},
            ],
        }
        mocker.patch('live.telegram_bot.requests.get', return_value=mock_response)
        
        updates = bot.get_updates()
        assert len(updates) == 1
        assert updates[0]['update_id'] == 1

    def test_get_updates_error(self, bot, mocker):
        """get_updates возвращает [] при ошибке."""
        mocker.patch(
            'live.telegram_bot.requests.get',
            side_effect=Exception('Network error'),
        )
        
        updates = bot.get_updates()
        assert updates == []

    def test_get_updates_non_200(self, bot, mocker):
        """get_updates возвращает [] при non-200."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mocker.patch('live.telegram_bot.requests.get', return_value=mock_response)
        
        updates = bot.get_updates()
        assert updates == []


class TestProcessUpdates:
    def test_process_updates_sends_response(self, bot, mocker):
        """process_updates отправляет ответ на команду."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': [
                {
                    'update_id': 1,
                    'message': {
                        'text': '/status',
                        'chat': {'id': '123456'},
                    },
                },
            ],
        }
        mocker.patch('live.telegram_bot.requests.get', return_value=mock_response)
        
        bot.process_updates()
        
        # Проверяем, что бот отправил ответ
        bot.notifier.send_message.assert_called_once()
        # Проверяем, что last_update_id обновился
        assert bot.last_update_id == 1

    def test_process_updates_ignores_other_chat(self, bot, mocker):
        """Сообщения из другого чата игнорируются."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': [
                {
                    'update_id': 1,
                    'message': {
                        'text': '/status',
                        'chat': {'id': '999999'},  # другой chat_id
                    },
                },
            ],
        }
        mocker.patch('live.telegram_bot.requests.get', return_value=mock_response)
        
        bot.process_updates()
        
        # Ответ НЕ должен отправляться
        bot.notifier.send_message.assert_not_called()

    def test_process_updates_unknown_command(self, bot, mocker):
        """Неизвестная команда не отправляет ответ."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': [
                {
                    'update_id': 1,
                    'message': {
                        'text': '/unknown_xyz',
                        'chat': {'id': '123456'},
                    },
                },
            ],
        }
        mocker.patch('live.telegram_bot.requests.get', return_value=mock_response)
        
        bot.process_updates()
        
        bot.notifier.send_message.assert_not_called()