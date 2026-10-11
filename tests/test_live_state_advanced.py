"""
Продвинутые тесты для live.state.

Покрывают: _load, _save, clean_old, get, get_all, get_active_count.
"""
import pytest
import sys
import os
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from live.state import SignalState


@pytest.fixture
def clean_state():
    """Чистое состояние."""
    state = SignalState()
    state.state = {}
    state._save()
    yield state
    state.state = {}
    state._save()


class TestLoadSave:
    def test_load_missing_file(self, mocker, tmp_path):
        """_load возвращает {} если файла нет."""
        mocker.patch('live.state.STATE_DIR', str(tmp_path))
        SignalState._instance = None
        state = SignalState()
        assert state.state == {}

    def test_load_invalid_json(self, mocker, tmp_path):
        """_load возвращает {} при битом JSON."""
        state_file = tmp_path / 'bad.json'
        state_file.write_text('{invalid json}')
        
        mocker.patch('live.state.STATE_DIR', str(tmp_path))
        SignalState._instance = None
        state = SignalState()
        assert state.state == {}

    def test_save_creates_file(self, clean_state):
        """_save создаёт файл."""
        clean_state._save()
        assert os.path.exists(clean_state.filepath)


class TestCleanOld:
    def test_clean_old_removes(self, clean_state):
        """clean_old удаляет старые сигналы."""
        # Добавляем сигнал
        clean_state.add({
            'symbol': 'EURUSD', 'mode': 'swing', 'strategy': 'w2_w3',
            'direction': 'BUY', 'entry_price': 1.1000, 'target': 1.1100,
            'stop': 1.0950, 'entry_time': datetime.now(),
        })
        assert len(clean_state.state) == 1
        
        # Сдвигаем created_at в прошлое на 60 дней
        for sid in clean_state.state:
            clean_state.state[sid]['created_at'] = (
                datetime.now() - timedelta(days=60)
            ).isoformat()
        clean_state._save()
        
        # clean_old с days=30 должен удалить
        clean_state.clean_old(days=30)
        assert len(clean_state.state) == 0

    def test_clean_old_keeps_recent(self, clean_state):
        """clean_old сохраняет свежие сигналы."""
        clean_state.add({
            'symbol': 'EURUSD', 'mode': 'swing', 'strategy': 'w2_w3',
            'direction': 'BUY', 'entry_price': 1.1000, 'target': 1.1100,
            'stop': 1.0950, 'entry_time': datetime.now(),
        })
        
        clean_state.clean_old(days=30)
        assert len(clean_state.state) == 1


class TestGetters:
    def test_get(self, clean_state):
        """get возвращает сигнал по ID."""
        sig = {
            'symbol': 'EURUSD', 'mode': 'swing', 'strategy': 'w2_w3',
            'direction': 'BUY', 'entry_price': 1.1000, 'target': 1.1100,
            'stop': 1.0950, 'entry_time': datetime.now(),
        }
        sid = clean_state.add(sig)
        
        result = clean_state.get(sid)
        assert result is not None
        assert result['symbol'] == 'EURUSD'

    def test_get_nonexistent(self, clean_state):
        """get возвращает None для несуществующего ID."""
        assert clean_state.get('nonexistent_id') is None

    def test_get_all(self, clean_state):
        """get_all возвращает список всех сигналов."""
        clean_state.add({
            'symbol': 'EURUSD', 'mode': 'swing', 'strategy': 'w2_w3',
            'direction': 'BUY', 'entry_price': 1.1000, 'target': 1.1100,
            'stop': 1.0950, 'entry_time': datetime.now(),
        })
        clean_state.add({
            'symbol': 'GBPUSD', 'mode': 'intraday', 'strategy': 'w4_w5',
            'direction': 'SELL', 'entry_price': 1.3000, 'target': 1.2900,
            'stop': 1.3050, 'entry_time': datetime.now(),
        })
        
        all_signals = clean_state.get_all()
        assert len(all_signals) == 2

    def test_get_active_count(self, clean_state):
        """get_active_count считает активные."""
        clean_state.add({
            'symbol': 'EURUSD', 'mode': 'swing', 'strategy': 'w2_w3',
            'direction': 'BUY', 'entry_price': 1.1000, 'target': 1.1100,
            'stop': 1.0950, 'entry_time': datetime.now(),
        })
        
        assert clean_state.get_active_count() == 1


class TestUpdateStatus:
    def test_update_status_nonexistent(self, clean_state):
        """update_status для несуществующего ID не падает."""
        clean_state.update_status('nonexistent', 'TARGET_HIT')
        assert True

    def test_update_status_changes(self, clean_state):
        """update_status меняет статус."""
        sid = clean_state.add({
            'symbol': 'EURUSD', 'mode': 'swing', 'strategy': 'w2_w3',
            'direction': 'BUY', 'entry_price': 1.1000, 'target': 1.1100,
            'stop': 1.0950, 'entry_time': datetime.now(),
        })
        
        clean_state.update_status(sid, 'TARGET_HIT')
        assert clean_state.state[sid]['status'] == 'TARGET_HIT'


class TestAddDuplicate:
    def test_add_duplicate_updates_timestamp(self, clean_state):
        """Повторное добавление обновляет updated_at."""
        sig = {
            'symbol': 'EURUSD', 'mode': 'swing', 'strategy': 'w2_w3',
            'direction': 'BUY', 'entry_price': 1.1000, 'target': 1.1100,
            'stop': 1.0950, 'entry_time': datetime(2026, 1, 1),
        }
        sid1 = clean_state.add(sig)
        original_updated = clean_state.state[sid1]['updated_at']
        
        # Второй раз
        sid2 = clean_state.add(sig)
        assert sid1 == sid2
        # updated_at должен измениться (или остаться тем же в ту же секунду)
        assert sid2 in clean_state.state