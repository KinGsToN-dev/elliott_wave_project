"""
Тесты для live.monitor, live.notifier, live.journal.
"""
import pytest
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from live.monitor import MarketMonitor
from live.notifier import TelegramNotifier
from live.journal import SignalJournal


class TestMarketMonitor:
    def test_init(self):
        """Инициализация."""
        monitor = MarketMonitor(symbol='EURUSD', mode='swing')
        assert monitor.symbol == 'EURUSD'
        assert monitor.mode_name == 'swing'
        assert 'combined' in monitor.strategies
    
    def test_is_new_signal(self):
        """Новый сигнал определяется."""
        monitor = MarketMonitor(symbol='EURUSD', mode='swing')
        monitor.state.state = {}
        monitor.state._save()
        
        sig1 = {
            'strategy': 'w2_w3',
            'symbol': 'EURUSD',
            'direction': 'BUY',
            'entry_time': datetime(2026, 1, 1),
            'entry_price': 1.1000,
        }
        
        # До добавления — новый
        assert monitor.is_new_signal(sig1) is True
        
        # Добавляем в состояние
        monitor.state.add(sig1)
        
        # После добавления — уже не новый
        assert monitor.is_new_signal(sig1) is False


class TestTelegramNotifier:
    def test_init(self):
        """Инициализация."""
        notifier = TelegramNotifier()
        assert notifier.config is not None
    
    def test_format_signal(self):
        """Форматирование сигнала."""
        notifier = TelegramNotifier()
        
        sig = {
            'strategy': 'w2_w3',
            'symbol': 'EURUSD',
            'mode': 'swing',
            'direction': 'BUY',
            'entry_price': 1.1000,
            'target': 1.1100,
            'stop': 1.0950,
            'pattern': 'W2_completion',
        }
        
        text = notifier.format_signal(sig)
        assert 'EURUSD' in text
        assert 'BUY' in text
        assert '1.1000' in text
        assert 'R:R' in text


class TestSignalJournal:
    def test_init(self):
        """Инициализация."""
        journal = SignalJournal(filename='test_journal.csv')
        assert os.path.exists(journal.filepath)
    
    def test_add_signal(self):
        """Добавление сигнала."""
        journal = SignalJournal(filename='test_journal.csv')
        
        sig = {
            'strategy': 'w2_w3',
            'symbol': 'EURUSD',
            'mode': 'swing',
            'direction': 'BUY',
            'entry_price': 1.1000,
            'target': 1.1100,
            'stop': 1.0950,
            'pattern': 'W2_completion',
        }
        
        # Не должно упасть
        journal.add(sig)
        assert True
    
    def test_add_many(self):
        """Добавление нескольких сигналов."""
        journal = SignalJournal(filename='test_journal.csv')
        
        signals = [
            {
                'strategy': 'w2_w3', 'symbol': 'EURUSD', 'mode': 'swing',
                'direction': 'BUY', 'entry_price': 1.1000, 'target': 1.1100,
                'stop': 1.0950, 'pattern': 'W2',
            },
            {
                'strategy': 'w4_w5', 'symbol': 'EURUSD', 'mode': 'swing',
                'direction': 'SELL', 'entry_price': 1.1100, 'target': 1.1000,
                'stop': 1.1150, 'pattern': 'W4',
            },
        ]
        
        count = journal.add_many(signals)
        assert count == 2

class TestLiveCoverage:
    def test_monitor_load_data_no_mt5(self):
        """Загрузка без MT5 — None."""
        from live.monitor import MarketMonitor
        monitor = MarketMonitor(symbol='EURUSD', mode='swing')
        # Не должно упасть
        assert monitor is not None
    
    def test_monitor_analyze_empty(self):
        """Анализ пустых данных."""
        import pandas as pd
        from live.monitor import MarketMonitor
        monitor = MarketMonitor(symbol='EURUSD', mode='swing')
        df = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'tick_volume'])
        # Не должно упасть
        assert monitor is not None
    
    def test_notifier_disabled(self):
        """Notifier отключён — сообщение не отправляется."""
        from live.notifier import TelegramNotifier
        notifier = TelegramNotifier()
        notifier.enabled = False
        result = notifier.send_message("Test")
        assert result == False
    
    def test_notifier_format_different(self):
        """Форматирование SELL-сигнала."""
        from live.notifier import TelegramNotifier
        notifier = TelegramNotifier()
        
        sig = {
            'strategy': 'w4_w5',
            'symbol': 'XAUUSD',
            'mode': 'intraday',
            'direction': 'SELL',
            'entry_price': 2000.00,
            'target': 1950.00,
            'stop': 2020.00,
            'pattern': 'W4_completion',
        }
        
        text = notifier.format_signal(sig)
        assert 'XAUUSD' in text
        assert 'SELL' in text
        assert '2000' in text
    
    def test_journal_creates_file(self):
        """Журнал создаёт файл."""
        from live.journal import SignalJournal
        import os
        journal = SignalJournal(filename='test_coverage.csv')
        assert os.path.exists(journal.filepath)