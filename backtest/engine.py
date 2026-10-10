"""
BacktestEngine - Движок симуляции сделок.

Принимает сигналы от стратегии, симулирует сделки на истории,
возвращает результаты.
"""
import pandas as pd
import numpy as np


class BacktestEngine:
    """Движок бэктеста."""
    
    def __init__(self, max_bars_hold=50, spread=0.0):
        """
        Args:
            max_bars_hold: максимум свечей удержания сделки
            spread: спред (в пунктах)
        """
        self.max_bars_hold = max_bars_hold
        self.spread = spread
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
        
        for time, row in after.iterrows():
            high = row['high']
            low = row['low']
            
            if direction == 'BUY':
                # Проверка цели
                if high >= target:
                    pnl = (target - entry_price) * 10000  # в пипсах
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
                # Проверка стопа
                if low <= stop:
                    pnl = (stop - entry_price) * 10000
                    return {
                        'entry_time': entry_time,
                        'entry_price': entry_price,
                        'exit_time': time,
                        'exit_price': stop,
                        'direction': direction,
                        'pnl': pnl,
                        'exit_reason': 'SL',
                        'bars_held': len(after.loc[:time]),
                    }
            else:  # SELL
                if low <= target:
                    pnl = (entry_price - target) * 10000
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
                if high >= stop:
                    pnl = (entry_price - stop) * 10000
                    return {
                        'entry_time': entry_time,
                        'entry_price': entry_price,
                        'exit_time': time,
                        'exit_price': stop,
                        'direction': direction,
                        'pnl': pnl,
                        'exit_reason': 'SL',
                        'bars_held': len(after.loc[:time]),
                    }
        
        # Время вышло — закрываем по последней цене
        last = after.iloc[-1]
        last_time = after.index[-1]
        
        if direction == 'BUY':
            pnl = (last['close'] - entry_price) * 10000
        else:
            pnl = (entry_price - last['close']) * 10000
        
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
