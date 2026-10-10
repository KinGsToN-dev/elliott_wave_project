"""
ZigZag - Построение ZigZag для поиска пивотов.
"""
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema

class ZigZag:
    def __init__(self, df, length=5):
        self.df = df.copy()
        self.length = length
        self.pivots = None
    
    def find_pivots(self):
        highs = self.df['high'].values
        lows = self.df['low'].values
        max_idx = argrelextrema(highs, np.greater, order=self.length)[0]
        min_idx = argrelextrema(lows, np.less, order=self.length)[0]
        pivots = []
        for i in max_idx:
            pivots.append((self.df.index[i], highs[i], 'high'))
        for i in min_idx:
            pivots.append((self.df.index[i], lows[i], 'low'))
        pivots.sort(key=lambda x: x[0])
        cleaned = []
        for p in pivots:
            if not cleaned:
                cleaned.append(p)
            else:
                last = cleaned[-1]
                if last[2] == p[2]:
                    if p[2] == 'high' and p[1] > last[1]:
                        cleaned[-1] = p
                    elif p[2] == 'low' and p[1] < last[1]:
                        cleaned[-1] = p
                else:
                    cleaned.append(p)
        self.pivots = pd.DataFrame(cleaned, columns=['time', 'price', 'type'])
        self.pivots.set_index('time', inplace=True)
        print(f"[OK] ZigZag (length={self.length}): найдено {len(self.pivots)} пивотов.")
        return self.pivots
    
    def get_zigzag_line(self):
        if self.pivots is None:
            self.find_pivots()
        return self.pivots[['price', 'type']]
