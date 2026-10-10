"""
Combinations - Комбинированные коррекции (W-X-Y, W-X-Y-X-Z).

Правила (traderevolution.by):
- Двойная тройка (W-X-Y): 3-3-3.
- Тройная тройка (W-X-Y-X-Z): 3-3-3-3-3.
- W и Y однонаправлены, X — против.
- W_X не заходит за начало W_W.
- W и Y эквивалентны по длине (в среднем).
"""
import pandas as pd


class CombinationDetector:
    """Детекция комбинированных коррекций."""
    
    def __init__(self, pivots, df=None, min_atr_ratio=1.0):
        self.pivots = pivots
        self.df = df
        self.min_atr_ratio = min_atr_ratio
        self.combinations = []
        self.atr = self._calculate_atr() if df is not None else None
    
    def _calculate_atr(self, period=14):
        if self.df is None:
            return None
        high = self.df['high']
        low = self.df['low']
        close = self.df['close']
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs()
        ], axis=1).max(axis=1)
        atr = tr.rolling(period).mean().iloc[-1]
        return float(atr) if not pd.isna(atr) else None
    
    def find_double_three(self):
        """
        Двойная тройка (W-X-Y).
        Требуется минимум 4 пивота.
        """
        prices = self.pivots['price'].values
        types = self.pivots['type'].values
        times = self.pivots.index
        
        doubles = []
        
        # 4 точки → range(len - 3)
        for i in range(len(prices) - 3):
            p0, p1, p2, p3 = prices[i], prices[i+1], prices[i+2], prices[i+3]
            t0, t1, t2, t3 = types[i], types[i+1], types[i+2], types[i+3]
            
            # W-X-Y структура требует:
            # bull: low → high → low → high
            # bear: high → low → high → low
            is_bullish = (t0 == 'low' and t1 == 'high' and t2 == 'low' and t3 == 'high')
            is_bearish = (t0 == 'high' and t1 == 'low' and t2 == 'high' and t3 == 'low')
            
            if not (is_bullish or is_bearish):
                continue
            
            w_len = abs(p1 - p0)
            x_len = abs(p2 - p1)
            y_len = abs(p3 - p2)
            total_size = w_len + x_len + y_len
            
            # ATR фильтр
            if self.atr is not None and self.atr > 0:
                if total_size < self.min_atr_ratio * self.atr:
                    continue
            
            # Правила:
            if is_bullish:
                x_no_break = bool(p2 > p0)
                same_direction = bool(p3 > p2 and p1 > p0)
            else:
                x_no_break = bool(p2 < p0)
                same_direction = bool(p3 < p2 and p1 < p0)
            
            # Пропорциональность W и Y
            if w_len > 0 and y_len > 0:
                proportional = bool(abs(w_len - y_len) / max(w_len, y_len) < 0.30)
            else:
                proportional = False
            
            valid = x_no_break and same_direction
            
            if valid:
                doubles.append({
                    'type': 'double_three',
                    'direction': 'bullish' if is_bullish else 'bearish',
                    'start_time': times[i],
                    'end_time': times[i + 3],
                    'points': [
                        (times[i],     p0, 'W'),
                        (times[i + 1], p1, 'X'),
                        (times[i + 2], p2, 'Y'),
                        (times[i + 3], p3, 'Y_end'),
                    ],
                    'w_len': w_len,
                    'x_len': x_len,
                    'y_len': y_len,
                    'size': total_size,
                    'rules': {
                        'x_no_break_w': x_no_break,
                        'same_direction': same_direction,
                        'proportional': proportional,
                    },
                })
        
        print(f"[OK] Двойных троек: {len(doubles)}")
        return doubles
    
    def find_triple_three(self):
        """
        Тройная тройка (W-X-Y-X-Z).
        Требуется минимум 6 пивотов.
        """
        prices = self.pivots['price'].values
        types = self.pivots['type'].values
        times = self.pivots.index
        
        triples = []
        
        # 6 точек → range(len - 5)
        for i in range(len(prices) - 5):
            p0, p1, p2, p3, p4, p5 = (prices[i], prices[i+1], prices[i+2], 
                                       prices[i+3], prices[i+4], prices[i+5])
            t0, t1, t2, t3, t4, t5 = (types[i], types[i+1], types[i+2], 
                                       types[i+3], types[i+4], types[i+5])
            
            # W-X-Y-X-Z: bull: low-high-low-high-low-high
            #             bear: high-low-high-low-high-low
            is_bullish = (t0 == 'low' and t1 == 'high' and t2 == 'low' 
                         and t3 == 'high' and t4 == 'low' and t5 == 'high')
            is_bearish = (t0 == 'high' and t1 == 'low' and t2 == 'high' 
                         and t3 == 'low' and t4 == 'high' and t5 == 'low')
            
            if not (is_bullish or is_bearish):
                continue
            
            w_len = abs(p1 - p0)
            x1_len = abs(p2 - p1)
            y_len = abs(p3 - p2)
            x2_len = abs(p4 - p3)
            z_len = abs(p5 - p4)
            total_size = w_len + x1_len + y_len + x2_len + z_len
            
            if self.atr is not None and self.atr > 0:
                if total_size < self.min_atr_ratio * self.atr * 1.5:
                    continue
            
            if is_bullish:
                x1_no_break = bool(p2 > p0)
                x2_no_break = bool(p4 > p2)
            else:
                x1_no_break = bool(p2 < p0)
                x2_no_break = bool(p4 < p2)
            
            valid = x1_no_break and x2_no_break
            
            if valid:
                triples.append({
                    'type': 'triple_three',
                    'direction': 'bullish' if is_bullish else 'bearish',
                    'start_time': times[i],
                    'end_time': times[i + 5],
                    'points': [
                        (times[i],     p0, 'W'),
                        (times[i + 1], p1, 'X'),
                        (times[i + 2], p2, 'Y'),
                        (times[i + 3], p3, 'X2'),
                        (times[i + 4], p4, 'Z'),
                        (times[i + 5], p5, 'Z_end'),
                    ],
                    'w_len': w_len,
                    'x1_len': x1_len,
                    'y_len': y_len,
                    'x2_len': x2_len,
                    'z_len': z_len,
                    'size': total_size,
                    'rules': {
                        'x1_no_break_w': x1_no_break,
                        'x2_no_break_y': x2_no_break,
                    },
                })
        
        print(f"[OK] Тройных троек: {len(triples)}")
        return triples
    
    def find_all(self):
        """Поиск всех комбинаций."""
        if self.pivots is None or len(self.pivots) < 4:
            print("[WARNING] Недостаточно пивотов для комбинаций")
            return []
        
        print(f"\n[INFO] Поиск комбинаций...")
        doubles = self.find_double_three()
        triples = self.find_triple_three()
        
        self.combinations = doubles + triples
        self.combinations = self._filter_overlaps(self.combinations)
        print(f"[OK] Найдено комбинаций (после фильтра): {len(self.combinations)}")
        return self.combinations
    
    def _filter_overlaps(self, combos):
        if not combos:
            return []
        sorted_c = sorted(combos, key=lambda x: x['size'], reverse=True)
        filtered = []
        for c in sorted_c:
            overlap = False
            for existing in filtered:
                if (c['start_time'] < existing['end_time'] and 
                    c['end_time'] > existing['start_time']):
                    overlap = True
                    break
            if not overlap:
                filtered.append(c)
        filtered.sort(key=lambda x: x['start_time'])
        return filtered
    
    def get_combinations(self):
        return self.combinations
