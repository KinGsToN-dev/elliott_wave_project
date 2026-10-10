"""
MTF Filter - Фильтр сигналов по старшему таймфрейму.

Для интрадей-режима проверяем глобальный тренд на H4.
Только сигналы в направлении тренда проходят фильтр.
"""
import pandas as pd
import numpy as np


class MTFFilter:
    """Фильтр сигналов по старшему ТФ."""
    
    def __init__(self, mtf_timeframe='H4', ema_len=200):
        self.mtf_timeframe = mtf_timeframe
        self.ema_len = ema_len
        self.trend = 'UNKNOWN'
        self.ema_value = None
        self.current_price = None
    
    def update_trend(self, mtf_data):
        """
        Обновляет тренд по данным старшего ТФ.
        
        Args:
            mtf_data: DataFrame со свечами старшего ТФ
        """
        if mtf_data is None or len(mtf_data) < 20:
            self.trend = 'UNKNOWN'
            return
        
        # EMA (или меньше, если данных мало)
        ema_len = min(self.ema_len, len(mtf_data) - 1)
        ema = mtf_data['close'].ewm(span=ema_len, adjust=False).mean()
        
        self.current_price = float(mtf_data['close'].iloc[-1])
        self.ema_value = float(ema.iloc[-1])
        
        if self.current_price > self.ema_value:
            self.trend = 'BULLISH'
        elif self.current_price < self.ema_value:
            self.trend = 'BEARISH'
        else:
            self.trend = 'NEUTRAL'
    
    def filter_signals(self, signals):
        """
        Фильтрует сигналы по тренду старшего ТФ.
        
        Args:
            signals: список сигналов
        
        Returns:
            отфильтрованный список
        """
        if self.trend == 'UNKNOWN' or self.trend == 'NEUTRAL':
            return signals  # нет фильтра
        
        filtered = []
        removed = 0
        
        for sig in signals:
            if self.trend == 'BULLISH' and sig['direction'] == 'BUY':
                filtered.append(sig)
            elif self.trend == 'BEARISH' and sig['direction'] == 'SELL':
                filtered.append(sig)
            else:
                removed += 1
        
        return filtered
    
    def get_summary(self):
        """Возвращает сводку по фильтру."""
        return {
            'mtf_timeframe': self.mtf_timeframe,
            'trend': self.trend,
            'ema_value': self.ema_value,
            'current_price': self.current_price,
        }
