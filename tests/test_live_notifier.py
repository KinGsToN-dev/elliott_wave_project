"""
Тесты для live.notifier (расширенные).

Покрывают: _load_config, send_message, format_signal, notify_signals.
"""
import pytest
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from live.notifier import TelegramNotifier


class TestLoadConfig:
    def test_load_config_missing_file(self, mocker):
        """_load_config возвращает {} если файла нет."""
        mocker.patch('live.notifier.CONFIG_FILE', 'C:/nonexistent/path.yaml')
        notifier = TelegramNotifier()
        assert notifier.config == {}

    def test_load_config_invalid_yaml(self, mocker, tmp_path):
        """_load_config возвращает {} при битом YAML."""
        config_file = tmp_path / 'bad.yaml'
        config_file.write_text('{[invalid yaml')
        mocker.patch('live.notifier.CONFIG_FILE', str(config_file))
        
        # Не должно упасть
        notifier = TelegramNotifier()
        # config = {} или {}
        assert isinstance(notifier.config, dict)


class TestSendMessage:
    def test_send_success(self, mocker):
        """send_message возвращает True при 200."""
        mocker.patch('live.notifier.requests.post')
        mock_response = MagicMock()
        mock_response.status_code = 200
        mocker.patch('live.notifier.requests.post', return_value=mock_response)
        
        notifier = TelegramNotifier()
        notifier.enabled = True
        notifier.bot_token = 'TEST'
        notifier.chat_id = '123'
        
        result = notifier.send_message("Test message")
        assert result is True

    def test_send_non_200(self, mocker):
        """send_message возвращает False при non-200."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mocker.patch('live.notifier.requests.post', return_value=mock_response)
        
        notifier = TelegramNotifier()
        notifier.enabled = True
        notifier.bot_token = 'TEST'
        notifier.chat_id = '123'
        
        result = notifier.send_message("Test")
        assert result is False

    def test_send_exception(self, mocker):
        """send_message возвращает False при исключении."""
        mocker.patch(
            'live.notifier.requests.post',
            side_effect=Exception('Network error'),
        )
        
        notifier = TelegramNotifier()
        notifier.enabled = True
        notifier.bot_token = 'TEST'
        notifier.chat_id = '123'
        
        result = notifier.send_message("Test")
        assert result is False

    def test_send_disabled(self, mocker):
        """send_message возвращает False если отключён."""
        notifier = TelegramNotifier()
        notifier.enabled = False
        
        result = notifier.send_message("Test")
        assert result is False


class TestFormatSignal:
    def test_format_eurusd(self):
        """format_signal для EURUSD."""
        notifier = TelegramNotifier()
        
        sig = {
            'strategy': 'w2_w3', 'symbol': 'EURUSD', 'mode': 'swing',
            'direction': 'BUY', 'entry_price': 1.1000,
            'target': 1.1100, 'stop': 1.0950, 'pattern': 'W2',
        }
        
        text = notifier.format_signal(sig)
        assert 'EURUSD' in text
        assert 'BUY' in text
        assert 'R:R' in text

    def test_format_usdjpy(self):
        """format_signal для USDJPY (другой pip multiplier)."""
        notifier = TelegramNotifier()
        
        sig = {
            'strategy': 'w2_w3', 'symbol': 'USDJPY', 'mode': 'swing',
            'direction': 'SELL', 'entry_price': 150.00,
            'target': 149.00, 'stop': 151.00, 'pattern': 'W4',
        }
        
        text = notifier.format_signal(sig)
        assert 'USDJPY' in text
        assert 'SELL' in text

    def test_format_xauusd(self):
        """format_signal для XAUUSD."""
        notifier = TelegramNotifier()
        
        sig = {
            'strategy': 'w4_w5', 'symbol': 'XAUUSD', 'mode': 'intraday',
            'direction': 'BUY', 'entry_price': 2000.00,
            'target': 2050.00, 'stop': 1980.00, 'pattern': 'W4_completion',
        }
        
        text = notifier.format_signal(sig)
        assert 'XAUUSD' in text
        assert 'BUY' in text

    def test_format_unknown_symbol(self):
        """format_signal для неизвестного символа — default multiplier."""
        notifier = TelegramNotifier()
        
        sig = {
            'strategy': 'w2_w3', 'symbol': 'UNKNOWN', 'mode': 'swing',
            'direction': 'BUY', 'entry_price': 1.0000,
            'target': 1.0100, 'stop': 0.9950, 'pattern': 'W2',
        }
        
        # Не должно упасть
        text = notifier.format_signal(sig)
        assert 'UNKNOWN' in text


class TestNotifySignals:
    def test_notify_signals_empty(self):
        """notify_signals с пустым списком — 0."""
        notifier = TelegramNotifier()
        result = notifier.notify_signals([])
        assert result == 0

    def test_notify_signals_with_mock(self, mocker):
        """notify_signals отправляет каждый сигнал."""
        notifier = TelegramNotifier()
        notifier.enabled = True
        notifier.bot_token = 'TEST'
        notifier.chat_id = '123'
        
        mocker.patch.object(notifier, 'send_message', return_value=True)
        
        signals = [
            {'symbol': 'EURUSD', 'strategy': 'w2_w3', 'mode': 'swing',
             'direction': 'BUY', 'entry_price': 1.1, 'target': 1.11,
             'stop': 1.095, 'pattern': 'W2'},
            {'symbol': 'GBPUSD', 'strategy': 'w2_w3', 'mode': 'swing',
             'direction': 'SELL', 'entry_price': 1.3, 'target': 1.29,
             'stop': 1.305, 'pattern': 'W4'},
        ]
        
        result = notifier.notify_signals(signals)
        assert result == 2
        assert notifier.send_message.call_count == 2

    def test_notify_signals_partial_failure(self, mocker):
        """notify_signals возвращает количество успешных."""
        notifier = TelegramNotifier()
        notifier.enabled = True
        notifier.bot_token = 'TEST'
        notifier.chat_id = '123'
        
        # Первый успех, второй провал
        mocker.patch.object(notifier, 'send_message', side_effect=[True, False])
        
        signals = [
            {'symbol': 'EURUSD', 'strategy': 'w2_w3', 'mode': 'swing',
             'direction': 'BUY', 'entry_price': 1.1, 'target': 1.11,
             'stop': 1.095, 'pattern': 'W2'},
            {'symbol': 'GBPUSD', 'strategy': 'w2_w3', 'mode': 'swing',
             'direction': 'SELL', 'entry_price': 1.3, 'target': 1.29,
             'stop': 1.305, 'pattern': 'W4'},
        ]
        
        result = notifier.notify_signals(signals)
        assert result == 1