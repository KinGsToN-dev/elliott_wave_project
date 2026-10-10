"""
BacktestEngine - Движок симуляции сделок.

Принимает сигналы от стратегии, симулирует сделки на истории,
возвращает результаты.
"""
import pandas as pd
import numpy as np

# ============================================================
# КОЭФФИЦИЕНТЫ ПИПСОВ ДЛЯ РАЗНЫХ СИМВОЛОВ
# ============================================================
# Для 5-значных валют (EURUSD, GBPUSD) — 10000
# Для 3-значных валют (USDJPY, EURJPY) — 100
# Для золота (XAUUSD) — 100
# Для серебра (XAGUSD) — 1000
# ============================================================
PIP_MULTIPLIER = {
    # 5-значные валюты
    'EURUSD': 10000,
    'GBPUSD': 10000,
    'AUDUSD': 10000,
    'NZDUSD': 10000,
    'USDCAD': 10000,
    'USDCHF': 10000,
    'EURGBP': 10000,
    'EURCHF': 10000,
    'EURCAD': 10000,
    'EURAUD': 10000,
    'GBPCHF': 10000,
    'GBPCAD': 10000,
    'GBPAUD': 10000,
    'AUDCAD': 10000,
    'AUDCHF': 10000,
    'AUDNZD': 10000,
    'NZDCAD': 10000,
    'NZDCHF': 10000,
    'CADCHF': 10000,
    
    # 3-значные валюты (JPY)
    'USDJPY': 100,
    'EURJPY': 100,
    'GBPJPY': 100,
    'AUDJPY': 100,
    'CADJPY': 100,
    'CHFJPY': 100,
    'NZDJPY': 100,
    
    # Металлы
    'XAUUSD': 100,    # Золото
    'XAGUSD': 1000,   # Серебро
    'XPTUSD': 100,    # Платина
    
    # Крипто (опционально)
    'BTCUSD': 1,
    'ETHUSD': 10,
}


class BacktestEngine:
    """Движок бэктеста."""
    
    def __init__(self, max_bars_hold=50, spread=0.0, symbol='EURUSD',
                 use_trailing_stop=False, trailing_trigger=0.5, trailing_distance=0.3):
        self.max_bars_hold = max_bars_hold
        self.spread = spread
        self.symbol = symbol
        self.pip_multiplier = PIP_MULTIPLIER.get(symbol, 10000)
        self.use_trailing_stop = use_trailing_stop
        self.trailing_trigger = trailing_trigger
        self.trailing_distance = trailing_distance
        self.trades = []
    
    def simulate_trade(self, signal, df):
        """
        Симулирует одну сделку.
        
        Args:
            signal: dict с entry_time, entry_price, direction, target, stop
            df: DataFrame со свечами
        
        Returns:
            dict с результатом: pnl, exit_reason, exit_time, exit_price
        """
        entry_time = pd.to_datetime(signal['entry_time'])
        entry_price = signal['entry_price']
        direction = signal['direction']
        target = signal['target']
        stop = signal['stop']
        
        # Свечи после входа
        try:
            after = df.loc[df.index > entry_time]
        except Exception:
            return None
        
        if len(after) == 0:
            return None
        
        # Ограничиваем горизонт
        after = after.head(self.max_bars_hold)
        
        # Начальный стоп (может двигаться при trailing)
        current_stop = stop
        stop_dist = abs(entry_price - stop)
        
        for time, row in after.iterrows():
            high = row['high']
            low = row['low']
            
            # ============================================================
            # TRAILING STOP
            # ============================================================
            if self.use_trailing_stop and stop_dist > 0:
                if direction == 'BUY':
                    # Прибыль по текущей свече
                    current_profit = high - entry_price
                    # Если прибыль >= trigger × stop_dist -> двигаем стоп
                    if current_profit >= stop_dist * self.trailing_trigger:
                        new_stop = high - stop_dist * self.trailing_distance
                        if new_stop > current_stop:
                            current_stop = new_stop
                else:  # SELL
                    current_profit = entry_price - low
                    if current_profit >= stop_dist * self.trailing_trigger:
                        new_stop = low + stop_dist * self.trailing_distance
                        if new_stop < current_stop:
                            current_stop = new_stop
            
            # ============================================================
            # ПРОВЕРКА ЦЕЛИ И СТОПА
            # ============================================================
            if direction == 'BUY':
                # Проверка цели
                if high >= target:
                    pnl = (target - entry_price) * self.pip_multiplier
                    return {
                        'entry_time': entry_time,
                        'entry_price': entry_price,
                        'exit_time': time,
                        'exit_price': target,
                        'direction': direction,
                        'pnl': pnl,
                        'exit_reason': 'TP',
                        'bars_held': len(after.loc[:time]),
                    }
                # Проверка стопа (текущего, с учётом trailing)
                if low <= current_stop:
                    pnl = (current_stop - entry_price) * self.pip_multiplier
                    return {
                        'entry_time': entry_time,
                        'entry_price': entry_price,
                        'exit_time': time,
                        'exit_price': current_stop,
                        'direction': direction,
                        'pnl': pnl,
                        'exit_reason': 'SL',
                        'bars_held': len(after.loc[:time]),
                    }
            else:  # SELL
                if low <= target:
                    pnl = (entry_price - target) * self.pip_multiplier
                    return {
                        'entry_time': entry_time,
                        'entry_price': entry_price,
                        'exit_time': time,
                        'exit_price': target,
                        'direction': direction,
                        'pnl': pnl,
                        'exit_reason': 'TP',
                        'bars_held': len(after.loc[:time]),
                    }
                if high >= current_stop:
                    pnl = (entry_price - current_stop) * self.pip_multiplier
                    return {
                        'entry_time': entry_time,
                        'entry_price': entry_price,
                        'exit_time': time,
                        'exit_price': current_stop,
                        'direction': direction,
                        'pnl': pnl,
                        'exit_reason': 'SL',
                        'bars_held': len(after.loc[:time]),
                    }
        
        # Время вышло — закрываем по последней цене
        last = after.iloc[-1]
        last_time = after.index[-1]
        
        if direction == 'BUY':
            pnl = (last['close'] - entry_price) * self.pip_multiplier
        else:
            pnl = (entry_price - last['close']) * self.pip_multiplier
        
        return {
            'entry_time': entry_time,
            'entry_price': entry_price,
            'exit_time': last_time,
            'exit_price': last['close'],
            'direction': direction,
            'pnl': pnl,
            'exit_reason': 'TIME',
            'bars_held': len(after),
        }
    
    def run(self, signals, df):
        """
        Запускает бэктест на всех сигналах.
        
        Args:
            signals: список сигналов от стратегии
            df: DataFrame со свечами
        
        Returns:
            Список сделок с результатами
        """
        self.trades = []
        
        for signal in signals:
            result = self.simulate_trade(signal, df)
            if result is not None:
                self.trades.append(result)
        
        return self.trades
    
    def get_trades(self):
        return self.trades
