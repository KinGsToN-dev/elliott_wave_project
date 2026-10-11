"""
MultiLiveRunner - Live-режим для нескольких символов и режимов.
"""
import sys
import os
import time
import threading
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from live.monitor import MarketMonitor
from live.notifier import TelegramNotifier
from live.journal import SignalJournal
from live.state import SignalState
from live.telegram_bot import TelegramBot


class MultiLiveRunner:
    """Live-режим для нескольких комбинаций."""
    
    def __init__(self, symbols=None, modes=None, strategies=None,
                 candles=500, interval=300, max_age_hours=168):
        # Дефолтные значения
        if symbols is None:
            symbols = ['EURUSD']
        if modes is None:
            modes = ['swing']
        
        self.symbols = symbols
        self.modes = modes
        self.interval = interval
        
        # Создаём мониторы для всех комбинаций
        self.monitors = []
        for symbol in symbols:
            for mode in modes:
                try:
                    monitor = MarketMonitor(
                        symbol=symbol,
                        mode=mode,
                        strategies=strategies,
                        candles=candles,
                        interval=interval,
                    )
                    self.monitors.append(monitor)
                except Exception as e:
                    print(f"[WARN] {symbol} {mode}: {e}")
        
        # Общие компоненты
        self.notifier = TelegramNotifier()
        self.journal = SignalJournal()
        self.state = SignalState()
        
        # Telegram-бот (в отдельном потоке)
        self.bot = TelegramBot()
        
        print(f"\n[INIT] MultiLiveRunner")
        print(f"[INIT] Символы: {symbols}")
        print(f"[INIT] Режимы: {modes}")
        print(f"[INIT] Всего комбинаций: {len(self.monitors)}")
    
    def _bot_thread(self):
        """Поток для Telegram-бота."""
        try:
            self.bot.run()
        except Exception as e:
            print(f"[ERROR] Bot thread: {e}")
    
    def run(self):
        """Запускает мониторинг."""
        print(f"\n{'=' * 60}")
        print(f" MULTI LIVE MODE — ЗАПУСК")
        print(f" {len(self.monitors)} комбинаций")
        print(f"{'=' * 60}\n")
        
        # Запускаем бота в отдельном потоке
        bot_thread = threading.Thread(target=self._bot_thread, daemon=True)
        bot_thread.start()
        
        try:
            while True:
                all_new_signals = []
                
                for monitor in self.monitors:
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] {monitor.symbol} | {monitor.mode_name}")
                    
                    try:
                        new_signals = monitor.run_once()
                        
                        if new_signals:
                            print(f"  Новых: {len(new_signals)}")
                            all_new_signals.extend(new_signals)
                    except Exception as e:
                        print(f"  [ERROR] {e}")
                
                # Отправка в Telegram
                if all_new_signals:
                    print(f"\n{'*' * 60}")
                    print(f" ВСЕГО НОВЫХ: {len(all_new_signals)}")
                    print(f"{'*' * 60}")
                    
                    self.notifier.notify_signals(all_new_signals)
                    self.journal.add_many(all_new_signals)
                    self.state.add_many(all_new_signals)
                
                print(f"\n[INFO] Ожидание {self.interval} сек...")
                time.sleep(self.interval)
        
        except KeyboardInterrupt:
            print(f"\n[INFO] Остановлено")
