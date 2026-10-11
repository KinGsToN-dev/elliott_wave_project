"""Тестовый сигнал в Telegram."""
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from live.notifier import TelegramNotifier

notifier = TelegramNotifier()

# Тестовый сигнал
test_signal = {
    'strategy': 'w2_w3',
    'symbol': 'EURUSD',
    'mode': 'swing',
    'direction': 'BUY',
    'entry_price': 1.1000,
    'target': 1.1100,
    'stop': 1.0950,
    'pattern': 'W2_completion',
    'entry_time': datetime.now(),
}

print("[TEST] Отправка тестового сигнала...")
notifier.notify_signal(test_signal)
print("[TEST] Готово!")
