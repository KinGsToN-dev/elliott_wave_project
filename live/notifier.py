"""
Notifier - Отправка уведомлений в Telegram.

Использует Telegram Bot API.
"""
import sys
import os
import requests
import yaml
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'config', 'telegram.yaml'
)


class TelegramNotifier:
    """Отправка уведомлений в Telegram."""
    
    def __init__(self):
        self.config = self._load_config()
        self.bot_token = self.config.get('bot_token', '')
        self.chat_id = self.config.get('chat_id', '')
        self.enabled = self.config.get('enabled', False)
        self.parse_mode = self.config.get('parse_mode', 'HTML')
        
        if not self.enabled:
            print("[WARN] Telegram отключён в config")
        elif not self.bot_token or self.bot_token == 'ВАШ_ТОКЕН_ЗДЕСЬ':
            print("[WARN] Telegram токен не указан")
            self.enabled = False
        else:
            print(f"[OK] Telegram готов (chat_id: {self.chat_id})")
    
    def _load_config(self):
        """Загружает конфиг из YAML."""
        if not os.path.exists(CONFIG_FILE):
            print(f"[WARN] Файл не найден: {CONFIG_FILE}")
            return {}
        
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            print(f"[ERROR] Битый YAML в {CONFIG_FILE}: {e}")
            return {}
        except Exception as e:
            print(f"[ERROR] Ошибка чтения {CONFIG_FILE}: {e}")
            return {}
    
    def send_message(self, text):
        """Отправляет сообщение в Telegram."""
        if not self.enabled:
            print("[SKIP] Telegram отключён")
            print(text)  # Печатаем в консоль
            return False
        
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': self.parse_mode,
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                print(f"[OK] Сообщение отправлено в Telegram")
                return True
            else:
                print(f"[ERROR] Ошибка отправки: {response.status_code}")
                return False
        except Exception as e:
            print(f"[ERROR] Ошибка: {e}")
            return False
    
    def format_signal(self, signal):
        """Форматирует сигнал для отправки."""
        strategy = signal.get('strategy', '?')
        symbol = signal.get('symbol', '?')
        mode = signal.get('mode', '?')
        direction = signal.get('direction', '?')
        
        entry_price = signal.get('entry_price', 0)
        target = signal.get('target', 0)
        stop = signal.get('stop', 0)
        pattern = signal.get('pattern', '?')
        
        # Расчёт R:R
        from backtest.engine import PIP_MULTIPLIER
        
        symbol_for_pips = signal.get('symbol', 'EURUSD')
        pip_mult = PIP_MULTIPLIER.get(symbol_for_pips, 10000)
        
        risk_pips = abs(entry_price - stop) * pip_mult
        reward_pips = abs(target - entry_price) * pip_mult
        rr = reward_pips / risk_pips if risk_pips > 0 else 0
        
        # Эмодзи
        if direction == 'BUY':
            emoji = "🟢"
            dir_text = "BUY (вверх)"
        else:
            emoji = "🔴"
            dir_text = "SELL (вниз)"
        
        text = f"""
{emoji} <b>СИГНАЛ — {symbol}</b>

📊 <b>Режим:</b> {mode}
📈 <b>Стратегия:</b> {strategy}
🎯 <b>Паттерн:</b> {pattern}

━━━━━━━━━━━━━━━━━━━━

💰 <b>Направление:</b> {dir_text}
📍 <b>Вход:</b> {entry_price:.5f}
🎯 <b>Цель:</b> {target:.5f} ({reward_pips:.0f} pips)
🛑 <b>Стоп:</b> {stop:.5f} ({risk_pips:.0f} pips)

📊 <b>R:R = {rr:.2f}</b>

━━━━━━━━━━━━━━━━━━━━
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        return text.strip()
    
    def notify_signal(self, signal):
        """Отправляет сигнал в Telegram."""
        text = self.format_signal(signal)
        return self.send_message(text)
    
    def notify_signals(self, signals):
        """Отправляет несколько сигналов."""
        if not signals:
            return 0
        
        count = 0
        for sig in signals:
            if self.notify_signal(sig):
                count += 1
        
        return count
