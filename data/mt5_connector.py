"""
MT5 Connector - Подключение к MetaTrader 5 и загрузка данных.
"""
import os
import sys
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Попытка импорта MetaTrader5 (может не работать на Python 3.12)
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    print("[WARNING] MetaTrader5 не установлен. Работаем в тестовом режиме с CSV.")


class MT5Connector:
    def __init__(self, symbol="EURUSD", timeframe=None):
        self.symbol = symbol
        self.timeframe = timeframe if timeframe else (mt5.TIMEFRAME_H1 if MT5_AVAILABLE else None)
        self.connected = False
    
    def connect(self):
        if not MT5_AVAILABLE:
            print("[WARNING] MT5 недоступен. Используйте load_from_csv() для теста.")
            return False
        if not mt5.initialize():
            print(f"[ERROR] MT5 initialize() failed, error code = {mt5.last_error()}")
            return False
        if not mt5.symbol_select(self.symbol, True):
            print(f"[ERROR] Symbol {self.symbol} not found!")
            mt5.shutdown()
            return False
        self.connected = True
        print(f"[OK] Подключено к MT5. Символ: {self.symbol}")
        return True
    
    def disconnect(self):
        if self.connected and MT5_AVAILABLE:
            mt5.shutdown()
            self.connected = False
            print("[OK] Отключено от MT5.")
    
    def get_candles(self, count=1000, start_date=None):
        if not MT5_AVAILABLE:
            print("[ERROR] MetaTrader5 недоступен!")
            return None
        if not self.connected:
            print("[ERROR] Нет подключения к MT5!")
            return None
        if start_date:
            rates = mt5.copy_rates_from(self.symbol, self.timeframe, start_date, count)
        else:
            rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, count)
        if rates is None:
            print(f"[ERROR] Не удалось загрузить свечи: {mt5.last_error()}")
            return None
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        print(f"[OK] Загружено {len(df)} свечей.")
        return df
    
    def save_to_csv(self, df, filename="candles.csv"):
        cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache", filename)
        df.to_csv(cache_path)
        print(f"[OK] Данные сохранены в {cache_path}")
    
    def load_from_csv(self, filename="candles.csv"):
        cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache", filename)
        if os.path.exists(cache_path):
            df = pd.read_csv(cache_path, index_col='time', parse_dates=True)
            print(f"[OK] Загружено {len(df)} свечей из кэша.")
            return df
        print(f"[ERROR] Файл не найден: {cache_path}")
        return None


def generate_test_data(count=500):
    """Генерация тестовых данных (если MT5 недоступен)."""
    import numpy as np
    from datetime import datetime, timedelta
    
    print("[INFO] Генерация тестовых данных...")
    dates = [datetime.now() - timedelta(hours=i) for i in range(count, 0, -1)]
    np.random.seed(42)
    
    price = 1.1000
    prices = []
    for _ in range(count):
        change = np.random.randn() * 0.001
        price += change
        prices.append(price)
    
    df = pd.DataFrame({
        'open': prices,
        'high': [p + abs(np.random.randn() * 0.0005) for p in prices],
        'low':  [p - abs(np.random.randn() * 0.0005) for p in prices],
        'close': [p + np.random.randn() * 0.0005 for p in prices],
        'tick_volume': [np.random.randint(100, 1000) for _ in range(count)]
    }, index=dates)
    df.index.name = 'time'
    
    print(f"[OK] Сгенерировано {len(df)} тестовых свечей.")
    return df
