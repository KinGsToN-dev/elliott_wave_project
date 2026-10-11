"""
Journal - Журнал сигналов в CSV.
"""
import os
import csv
from datetime import datetime


JOURNAL_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'logs'
)


class SignalJournal:
    """Журнал сигналов."""
    
    def __init__(self, filename=None):
        if filename is None:
            filename = f"signals_{datetime.now().strftime('%Y%m%d')}.csv"
        
        os.makedirs(JOURNAL_DIR, exist_ok=True)
        self.filepath = os.path.join(JOURNAL_DIR, filename)
        
        # Заголовки
        self.headers = [
            'timestamp', 'symbol', 'mode', 'strategy', 'pattern',
            'direction', 'entry_price', 'target', 'stop', 'r_r'
        ]
        
        # Создаём файл с заголовками
        if not os.path.exists(self.filepath):
            with open(self.filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(self.headers)
        
        print(f"[OK] Журнал: {self.filepath}")
    
    def add(self, signal):
        """Добавляет сигнал в журнал."""
        entry = signal.get('entry_price', 0)
        target = signal.get('target', 0)
        stop = signal.get('stop', 0)
        
        risk = abs(entry - stop)
        reward = abs(target - entry)
        rr = reward / risk if risk > 0 else 0
        
        row = [
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            signal.get('symbol', ''),
            signal.get('mode', ''),
            signal.get('strategy', ''),
            signal.get('pattern', ''),
            signal.get('direction', ''),
            f"{entry:.5f}",
            f"{target:.5f}",
            f"{stop:.5f}",
            f"{rr:.2f}",
        ]
        
        with open(self.filepath, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(row)
    
    def add_many(self, signals):
        """Добавляет несколько сигналов."""
        for sig in signals:
            self.add(sig)
        return len(signals)
