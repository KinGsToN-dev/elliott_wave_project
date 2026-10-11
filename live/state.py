"""
State - Управление состоянием сигналов.

Хранит все сигналы в JSON-файле.
Singleton — один экземпляр на всё приложение.
"""
import os
import json
from datetime import datetime, timedelta


STATE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'state'
)


class SignalState:
    """Управление состоянием сигналов (Singleton)."""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Singleton — всегда один экземпляр."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, filename='signals_state.json'):
        if self._initialized:
            return
        self._initialized = True
        
        os.makedirs(STATE_DIR, exist_ok=True)
        self.filepath = os.path.join(STATE_DIR, filename)
        self.state = self._load()
    
    def _load(self):
        """Загружает состояние из файла."""
        if not os.path.exists(self.filepath):
            return {}
        
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    
    def _save(self):
        """Сохраняет состояние в файл."""
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)
    
    def _make_id(self, signal):
        """Создаёт уникальный ID сигнала."""
        entry_time = signal.get('entry_time')
        if hasattr(entry_time, 'strftime'):
            entry_time = entry_time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            entry_time = str(entry_time)[:19]
        
        return (
            f"{signal.get('symbol', '?')}_"
            f"{signal.get('mode', '?')}_"
            f"{signal.get('strategy', '?')}_"
            f"{entry_time}"
        )
    
    def add(self, signal):
        """Добавляет сигнал в состояние."""
        sid = self._make_id(signal)
        
        if sid in self.state:
            self.state[sid]['updated_at'] = datetime.now().isoformat()
        else:
            entry = signal.get('entry_price', 0)
            target = signal.get('target', 0)
            stop = signal.get('stop', 0)
            
            try:
                from backtest.engine import PIP_MULTIPLIER
                pip_mult = PIP_MULTIPLIER.get(signal.get('symbol', 'EURUSD'), 10000)
            except Exception:
                pip_mult = 10000
            
            risk_pips = abs(entry - stop) * pip_mult
            reward_pips = abs(target - entry) * pip_mult
            rr = reward_pips / risk_pips if risk_pips > 0 else 0
            
            self.state[sid] = {
                'id': sid,
                'symbol': signal.get('symbol', '?'),
                'mode': signal.get('mode', '?'),
                'strategy': signal.get('strategy', '?'),
                'pattern': signal.get('pattern', '?'),
                'direction': signal.get('direction', '?'),
                'entry_price': entry,
                'target': target,
                'stop': stop,
                'entry_time': str(signal.get('entry_time', '')),
                'status': 'ACTIVE',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'r_r': round(rr, 2),
                'pips_target': round(reward_pips),
                'pips_stop': round(risk_pips),
            }
        
        self._save()
        return sid
    
    def add_many(self, signals):
        """Добавляет несколько сигналов."""
        for sig in signals:
            self.add(sig)
    
    def get(self, sid):
        """Возвращает сигнал по ID."""
        return self.state.get(sid)
    
    def get_all(self):
        """Возвращает все сигналы."""
        return list(self.state.values())
    
    def get_active(self, mode=None, symbol=None):
        """Возвращает активные сигналы."""
        active = [
            s for s in self.state.values()
            if s['status'] == 'ACTIVE'
        ]
        
        if mode:
            active = [s for s in active if s['mode'] == mode]
        if symbol:
            active = [s for s in active if s['symbol'] == symbol]
        
        return active


    def get_active_count(self):
        """Быстрый подсчёт активных сигналов."""
        return len([s for s in self.state.values() if s['status'] == 'ACTIVE'])
    
    def update_status(self, sid, status):
        """Обновляет статус сигнала."""
        if sid in self.state:
            self.state[sid]['status'] = status
            self.state[sid]['updated_at'] = datetime.now().isoformat()
            self._save()
    
    def clean_old(self, days=30):
        """Удаляет старые сигналы."""
        cutoff = datetime.now() - timedelta(days=days)
        
        new_state = {}
        for sid, sig in self.state.items():
            try:
                created = datetime.fromisoformat(sig['created_at'])
                if created > cutoff:
                    new_state[sid] = sig
            except Exception:
                new_state[sid] = sig
        
        self.state = new_state
        self._save()
    
    def get_stats(self):
        """Возвращает статистику."""
        total = len(self.state)
        active = len([s for s in self.state.values() if s['status'] == 'ACTIVE'])
        target_hit = len([s for s in self.state.values() if s['status'] == 'TARGET_HIT'])
        stop_hit = len([s for s in self.state.values() if s['status'] == 'STOP_HIT'])
        
        return {
            'total': total,
            'active': active,
            'target_hit': target_hit,
            'stop_hit': stop_hit,
            'winrate': target_hit / (target_hit + stop_hit) if (target_hit + stop_hit) > 0 else 0,
        }
