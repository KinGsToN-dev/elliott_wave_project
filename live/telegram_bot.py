"""
Telegram Bot - Обработка команд от пользователя.

Позволяет запрашивать сигналы, статистику, статус.
"""
import sys
import os
import time
import requests
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from live.state import SignalState
from live.notifier import TelegramNotifier


class TelegramBot:
    """Telegram-бот с командами."""
    
    def __init__(self):
        self.notifier = TelegramNotifier()
        self.state = SignalState()
        
        self.bot_token = self.notifier.bot_token
        self.chat_id = self.notifier.chat_id
        
        self.last_update_id = 0
        self.running = False
    
    def get_updates(self):
        """Получает новые сообщения от Telegram."""
        url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
        params = {
            'offset': self.last_update_id + 1,
            'timeout': 10,
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                return data.get('result', [])
        except Exception as e:
            print(f"[ERROR] Telegram: {e}")
        
        return []
    
    def send_message(self, text):
        """Отправляет сообщение."""
        return self.notifier.send_message(text)
    
    def handle_command(self, text):
        """Обрабатывает команду."""
        text = text.strip().lower()
        
        # /start
        if text == '/start':
            return (
                "🤖 <b>Elliott Wave Bot</b>\n\n"
                "Доступные команды:\n"
                "/status — статус системы\n"
                "/signals — все актуальные сигналы\n"
                "/signals_swing — swing\n"
                "/signals_intraday — intraday\n"
                "/signals_scalping — scalping\n"
                "/history [N] — последние N сигналов из журнала\n"
                "/stats — статистика\n"
                "/stop — остановить бота\n"
                "/help — помощь"
            )
        
        # /help
        elif text == '/help':
            return (
                "📋 <b>Команды:</b>\n\n"
                "/status — статус\n"
                "/signals — все сигналы\n"
                "/signals_swing — swing\n"
                "/signals_intraday — intraday\n"
                "/signals_scalping — scalping\n"
                "/history [N] — последние N сигналов\n"
                "/stats — статистика\n"
                "/stop — остановить бота"
            )
        
        # /status
        elif text == '/status':
            active = self.state.get_active()
            stats = self.state.get_stats()
            
            return (
                f"📊 <b>Статус системы</b>\n\n"
                f"🟢 Активных сигналов: {len(active)}\n"
                f"📈 Всего сигналов: {stats['total']}\n"
                f"✅ Целей достигнуто: {stats['target_hit']}\n"
                f"❌ Стопов сработало: {stats['stop_hit']}\n"
                f"📊 Winrate: {stats['winrate']*100:.1f}%\n\n"
                f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        
        # /signals
        elif text == '/signals':
            active = self.state.get_active()
            
            if not active:
                return "📭 Нет актуальных сигналов"
            
            text_result = f"📊 <b>Актуальные сигналы ({len(active)})</b>\n\n"
            
            for sig in active[-10:]:  # последние 10
                direction_emoji = "🟢" if sig['direction'] == 'BUY' else "🔴"
                text_result += (
                    f"{direction_emoji} <b>{sig['symbol']}</b> "
                    f"({sig['mode']}) — {sig['strategy']}\n"
                    f"   Вход: {sig['entry_price']:.5f}\n"
                    f"   Цель: {sig['target']:.5f} ({sig['pips_target']} pips)\n"
                    f"   R:R: {sig['r_r']}\n\n"
                )
            
            return text_result.strip()
        
        # /signals_swing
        elif text == '/signals_swing':
            active = self.state.get_active(mode='swing')
            return self._format_signals(active, 'Swing')
        
        # /signals_intraday
        elif text == '/signals_intraday':
            active = self.state.get_active(mode='intraday')
            return self._format_signals(active, 'Intraday')
        
        # /signals_scalping
        elif text == '/signals_scalping':
            active = self.state.get_active(mode='scalping')
            return self._format_signals(active, 'Scalping')
        
        elif text == '/stats':
            stats = self.state.get_stats()
            
            return (
                f"📊 <b>Статистика</b>\n\n"
                f"📈 Всего: {stats['total']}\n"
                f"🟢 Активных: {stats['active']}\n"
                f"✅ Целей: {stats['target_hit']}\n"
                f"❌ Стопов: {stats['stop_hit']}\n"
                f"📊 Winrate: {stats['winrate']*100:.1f}%"
            )
        
        # /stop
        elif text == '/stop':
            self.running = False
            return (
                f"🛑 <b>Бот остановлен</b>\n\n"
                f"Всего сигналов в состоянии: {len(self.state.state)}\n"
                f"Для перезапуска запустите runner заново."
            )
        
        # /history [N]
        elif text.startswith('/history'):
            parts = text.split()
            try:
                n = int(parts[1]) if len(parts) > 1 else 10
            except (ValueError, IndexError):
                n = 10
            return self._read_history(n)
        
        # неизвестная команда
        else:
            return None  # не отвечаем
    
    def _read_history(self, n=10):
        """Читает последние N сигналов из CSV-журнала."""
        import csv
        from datetime import datetime
        
        today = datetime.now().strftime('%Y%m%d')
        filepath = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'logs', f'signals_{today}.csv'
        )
        
        if not os.path.exists(filepath):
            return f"📭 История за {today} пуста"
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                rows = list(csv.DictReader(f))
        except Exception as e:
            return f"❌ Ошибка чтения журнала: {e}"
        
        if not rows:
            return "📭 История пуста"
        
        # Берём последние N
        last = rows[-n:]
        
        text = f"📜 <b>Последние {len(last)} сигналов:</b>\n\n"
        for row in last:
            direction_emoji = "🟢" if row.get('direction') == 'BUY' else "🔴"
            text += (
                f"{direction_emoji} <b>{row.get('symbol', '?')}</b> "
                f"{row.get('mode', '?')} — {row.get('strategy', '?')}\n"
                f"   {row.get('direction', '?')} @ {row.get('entry_price', '?')} "
                f"→ {row.get('target', '?')}\n"
                f"   R:R {row.get('r_r', '?')}\n\n"
            )
        
        return text.strip()

    def _read_history(self, n=10):
        """Читает последние N сигналов из CSV-журнала."""
        import csv
        from datetime import datetime
        
        today = datetime.now().strftime('%Y%m%d')
        filepath = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'logs', f'signals_{today}.csv'
        )
        
        if not os.path.exists(filepath):
            return f"📭 История за {today} пуста"
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                rows = list(csv.DictReader(f))
        except Exception as e:
            return f"❌ Ошибка чтения журнала: {e}"
        
        if not rows:
            return "📭 История пуста"
        
        last = rows[-n:]
        
        text = f"📜 <b>Последние {len(last)} сигналов:</b>\n\n"
        for row in last:
            direction_emoji = "🟢" if row.get('direction') == 'BUY' else "🔴"
            text += (
                f"{direction_emoji} <b>{row.get('symbol', '?')}</b> "
                f"{row.get('mode', '?')} — {row.get('strategy', '?')}\n"
                f"   {row.get('direction', '?')} @ {row.get('entry_price', '?')} "
                f"→ {row.get('target', '?')}\n"
                f"   R:R {row.get('r_r', '?')}\n\n"
            )
        
        return text.strip()

    def _format_signals(self, signals, title):
        """Форматирует список сигналов."""
        if not signals:
            return f"📭 Нет сигналов в режиме {title}"
        
        text = f"📊 <b>{title} ({len(signals)})</b>\n\n"
        
        for sig in signals[-10:]:
            direction_emoji = "🟢" if sig['direction'] == 'BUY' else "🔴"
            text += (
                f"{direction_emoji} <b>{sig['symbol']}</b> — {sig['strategy']}\n"
                f"   Вход: {sig['entry_price']:.5f}\n"
                f"   Цель: {sig['target']:.5f} ({sig['pips_target']} pips)\n"
                f"   R:R: {sig['r_r']}\n\n"
            )
        
        return text.strip()
    
    def process_updates(self):
        """Обрабатывает входящие сообщения."""
        updates = self.get_updates()
        
        for update in updates:
            self.last_update_id = update.get('update_id', 0)
            
            message = update.get('message', {})
            text = message.get('text', '')
            chat_id = str(message.get('chat', {}).get('id', ''))
            
            # Проверяем, что сообщение от нашего chat_id
            if chat_id != str(self.chat_id):
                continue
            
            # Обрабатываем команду
            response = self.handle_command(text)
            
            if response:
                self.send_message(response)
                print(f"[TELEGRAM] Ответ на: {text}")
    
    def run(self):
        """Запускает бота в цикле."""
        print(f"\n{'=' * 60}")
        print(f" TELEGRAM BOT ЗАПУЩЕН")
        print(f" Chat ID: {self.chat_id}")
        print(f"{'=' * 60}\n")
        
        self.running = True
        
        try:
            while self.running:
                self.process_updates()
                time.sleep(2)  # проверяем каждые 2 сек
        
        except KeyboardInterrupt:
            print(f"\n[INFO] Бот остановлен")
            self.running = False
