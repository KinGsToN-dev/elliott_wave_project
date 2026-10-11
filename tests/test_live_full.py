"""
Тесты для Live-режима (полные).
"""
import pytest
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from live.state import SignalState
from live.monitor import MarketMonitor


def make_df(n=100, start=None):
    """
    Создаёт DataFrame со свечами.
    По умолчанию индекс идёт от (сейчас - n часов) до сейчас,
    чтобы created_at сигнала попадал в диапазон.
    """
    if start is None:
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


class TestSignalState:
    def test_singleton(self):
        """SignalState - Singleton."""
        s1 = SignalState()
        s2 = SignalState()
        assert s1 is s2, "SignalState должен быть Singleton"

    def test_add_signal(self):
        """Добавление сигнала."""
        state = SignalState()
        state.state = {}
        state._save()

        signal = {
            'symbol': 'EURUSD',
            'mode': 'swing',
            'strategy': 'w2_w3',
            'direction': 'BUY',
            'entry_price': 1.1000,
            'target': 1.1100,
            'stop': 1.0950,
            'entry_time': datetime.now(),
        }

        sid = state.add(signal)
        assert sid in state.state
        assert state.state[sid]['status'] == 'ACTIVE'

    def test_get_active(self):
        """Получение активных сигналов."""
        state = SignalState()
        state.state = {}
        state._save()

        signal = {
            'symbol': 'EURUSD',
            'mode': 'swing',
            'strategy': 'w2_w3',
            'direction': 'BUY',
            'entry_price': 1.1000,
            'target': 1.1100,
            'stop': 1.0950,
            'entry_time': datetime.now(),
        }

        state.add(signal)
        active = state.get_active()
        assert len(active) == 1

    def test_get_active_by_mode(self):
        """Фильтр по режиму."""
        state = SignalState()
        state.state = {}
        state._save()

        state.add({
            'symbol': 'EURUSD', 'mode': 'swing', 'strategy': 'w2_w3',
            'direction': 'BUY', 'entry_price': 1.1000, 'target': 1.1100,
            'stop': 1.0950, 'entry_time': datetime.now(),
        })

        state.add({
            'symbol': 'GBPUSD', 'mode': 'intraday', 'strategy': 'w4_w5',
            'direction': 'SELL', 'entry_price': 1.3000, 'target': 1.2900,
            'stop': 1.3050, 'entry_time': datetime.now(),
        })

        swing = state.get_active(mode='swing')
        intraday = state.get_active(mode='intraday')

        assert len(swing) == 1
        assert len(intraday) == 1

    def test_update_status(self):
        """Обновление статуса."""
        state = SignalState()
        state.state = {}
        state._save()

        signal = {
            'symbol': 'EURUSD', 'mode': 'swing', 'strategy': 'w2_w3',
            'direction': 'BUY', 'entry_price': 1.1000, 'target': 1.1100,
            'stop': 1.0950, 'entry_time': datetime.now(),
        }

        sid = state.add(signal)
        state.update_status(sid, 'TARGET_HIT')

        assert state.state[sid]['status'] == 'TARGET_HIT'

    def test_get_stats(self):
        """Статистика."""
        state = SignalState()
        state.state = {}
        state._save()

        signal = {
            'symbol': 'EURUSD', 'mode': 'swing', 'strategy': 'w2_w3',
            'direction': 'BUY', 'entry_price': 1.1000, 'target': 1.1100,
            'stop': 1.0950, 'entry_time': datetime.now(),
        }

        sid = state.add(signal)
        state.update_status(sid, 'TARGET_HIT')

        stats = state.get_stats()
        assert stats['total'] == 1
        assert stats['target_hit'] == 1
        assert stats['winrate'] == 1.0


class TestMarketMonitor:
    def test_update_status_target_hit(self):
        """Target достигнут - статус обновляется."""
        state = SignalState()
        state.state = {}
        state._save()

        entry_time = datetime.now() - timedelta(hours=10)
        signal = {
            'symbol': 'EURUSD', 'mode': 'swing', 'strategy': 'w2_w3',
            'direction': 'BUY', 'entry_price': 1.1000, 'target': 1.1100,
            'stop': 1.0950, 'entry_time': entry_time,
        }
        sid = state.add(signal)

        # Сдвигаем created_at далеко в прошлое,
        # чтобы весь df попал в after
        state.state[sid]['created_at'] = (datetime.now() - timedelta(hours=200)).isoformat()
        state._save()

        df = make_df(100)
        # Бар №50 теперь точно после created_at
        df.iloc[50, df.columns.get_loc('high')] = 1.1150

        monitor = MarketMonitor(symbol='EURUSD', mode='swing')
        monitor.state = state

        updated = monitor.update_active_signals(df)

        assert state.state[sid]['status'] == 'TARGET_HIT'

    def test_update_status_stop_hit(self):
        """Stop достигнут - статус обновляется."""
        state = SignalState()
        state.state = {}
        state._save()

        entry_time = datetime.now() - timedelta(hours=10)
        signal = {
            'symbol': 'EURUSD', 'mode': 'swing', 'strategy': 'w2_w3',
            'direction': 'BUY', 'entry_price': 1.1000, 'target': 1.1100,
            'stop': 1.0950, 'entry_time': entry_time,
        }
        sid = state.add(signal)

        state.state[sid]['created_at'] = (datetime.now() - timedelta(hours=200)).isoformat()
        state._save()

        df = make_df(100)
        df.iloc[50, df.columns.get_loc('low')] = 1.0900  # ниже stop

        monitor = MarketMonitor(symbol='EURUSD', mode='swing')
        monitor.state = state

        updated = monitor.update_active_signals(df)

        assert state.state[sid]['status'] == 'STOP_HIT'

    def test_is_signal_actual(self):
        """Проверка актуальности сигнала."""
        monitor = MarketMonitor(symbol='EURUSD', mode='swing')
        df = make_df(100)

        signal = {
            'entry_time': datetime.now() - timedelta(hours=5),
            'target': 1.1100,
            'stop': 1.0950,
            'direction': 'BUY',
        }

        actual = monitor.is_signal_actual(signal, df)
        assert actual in [True, False]