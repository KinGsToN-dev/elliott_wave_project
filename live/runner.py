"""
Runner - Запуск Live-режима.

Объединяет Monitor + Notifier + Journal.
"""
import sys
import os
import time
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from live.monitor import MarketMonitor
from live.notifier import TelegramNotifier
from live.journal import SignalJournal


class LiveRunner:
    """Запуск Live-режима."""
    
    def __init__(self, symbol='EURUSD', mode='intraday',
                 strategies=None, candles=500, interval=300):
        self.monitor = MarketMonitor(
            symbol=symbol,
            mode=mode,
            strategies=strategies,
            candles=candles,
            interval=interval,
        )
        self.notifier = TelegramNotifier()
        self.journal = SignalJournal()
    
    def run(self, max_iterations=None):
        """Запускает Live-режим."""
        print(f"\n{'=' * 60}")
        print(f" LIVE MODE — ЗАПУСК")
        print(f" {self.monitor.symbol} | {self.monitor.mode_name}")
        print(f" Интервал: {self.monitor.interval} сек")
        print(f"{'=' * 60}\n")
        
        try:
            for new_signals in self.monitor.run(max_iterations=max_iterations):
                if not new_signals:
                    continue
                
                print(f"\n{'*' * 60}")
                print(f" НОВЫЕ СИГНАЛЫ: {len(new_signals)}")
                print(f"{'*' * 60}")
                
                # Отправляем в Telegram
                sent = self.notifier.notify_signals(new_signals)
                print(f"[TELEGRAM] Отправлено: {sent}/{len(new_signals)}")
                
                # Сохраняем в журнал
                saved = self.journal.add_many(new_signals)
                print(f"[JOURNAL] Сохранено: {saved}")
        
        except KeyboardInterrupt:
            print(f"\n[INFO] Остановлено")
        
        print(f"\n{'=' * 60}")
        print(f" LIVE MODE — ЗАВЕРШЁН")
        print(f" Всего сигналов: {len(self.monitor.journal)}")
        print(f"{'=' * 60}")
