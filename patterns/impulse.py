"""
Impulse - Детекция импульсов (1-2-3-4-5).
Исправлено: bool вместо np.bool_, Extension логика.
"""
import pandas as pd
import numpy as np


class ImpulseDetector:
    def __init__(self, pivots, df=None, min_atr_ratio=1.5):
        self.pivots = pivots
        self.df = df
        self.min_atr_ratio = min_atr_ratio
        self.impulses = []
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
    
    def find_impulses(self):
        if self.pivots is None or len(self.pivots) < 6:
            print("[WARNING] Недостаточно пивотов для поиска импульсов.")
            return []
        
        prices = self.pivots['price'].values
        types = self.pivots['type'].values
        times = self.pivots.index
        
        for i in range(len(prices) - 5):
            p = prices[i:i+6]
            t = types[i:i+6]
            
            is_bullish = (t[0] == 'low' and t[1] == 'high' and t[2] == 'low' 
                         and t[3] == 'high' and t[4] == 'low' and t[5] == 'high')
            is_bearish = (t[0] == 'high' and t[1] == 'low' and t[2] == 'high' 
                         and t[3] == 'low' and t[4] == 'high' and t[5] == 'low')
            
            if not (is_bullish or is_bearish):
                continue
            
            impulse_size = abs(p[5] - p[0])
            
            # ATR фильтр (только если ATR доступен)
            if self.atr is not None and self.atr > 0:
                if impulse_size < self.min_atr_ratio * self.atr:
                    continue
            
            if is_bullish:
                result = self._check_bullish(p)
            else:
                result = self._check_bearish(p)
            
            if not result['valid']:
                continue
            
            impulse = {
                'start_idx': i,
                'start_time': times[i],
                'end_time': times[i + 5],
                'direction': 'bullish' if is_bullish else 'bearish',
                'points': [
                    (times[i],     p[0], '0'),
                    (times[i + 1], p[1], '1'),
                    (times[i + 2], p[2], '2'),
                    (times[i + 3], p[3], '3'),
                    (times[i + 4], p[4], '4'),
                    (times[i + 5], p[5], '5'),
                ],
                'w1': abs(p[1] - p[0]),
                'w2': abs(p[2] - p[1]),
                'w3': abs(p[3] - p[2]),
                'w4': abs(p[4] - p[3]),
                'w5': abs(p[5] - p[4]),
                'size': impulse_size,
                'extension': result['extension'],
                'truncated': bool(result['truncated']),  # ← bool()!
                'rules': result['rules'],
            }
            self.impulses.append(impulse)
        
        self.impulses = self._filter_overlaps(self.impulses)
        print(f"[OK] Найдено импульсов (после фильтра): {len(self.impulses)}")
        return self.impulses
    
    def _filter_overlaps(self, impulses):
        if not impulses:
            return []
        sorted_imp = sorted(impulses, key=lambda x: x['size'], reverse=True)
        filtered = []
        for imp in sorted_imp:
            overlap = False
            for existing in filtered:
                if (imp['start_time'] < existing['end_time'] and 
                    imp['end_time'] > existing['start_time']):
                    overlap = True
                    break
            if not overlap:
                filtered.append(imp)
        filtered.sort(key=lambda x: x['start_time'])
        return filtered
    
    def _compute_extension(self, w1, w3, w5):
        """Правильная логика растяжения: самая длинная >= 1.2 * вторая по длине."""
        lengths = {'W1': w1, 'W3': w3, 'W5': w5}
        sorted_vals = sorted(lengths.values(), reverse=True)
        if sorted_vals[1] > 0 and sorted_vals[0] >= sorted_vals[1] * 1.2:
            return max(lengths, key=lengths.get)
        return None
    
    def _check_bullish(self, p):
        p0, p1, p2, p3, p4, p5 = [float(x) for x in p]
        rules = {}
        valid = True
        
        rules['w2_no_break_w1'] = bool(p2 > p0)
        if not rules['w2_no_break_w1']: valid = False
        
        rules['w3_breaks_w1'] = bool(p3 > p1)
        if not rules['w3_breaks_w1']: valid = False
        
        rules['w4_no_overlap_w1'] = bool(p4 > p1)
        if not rules['w4_no_overlap_w1']: valid = False
        
        w1, w3, w5 = p1 - p0, p3 - p2, p5 - p4
        rules['w3_not_shortest'] = bool(w3 >= min(w1, w5))
        if not rules['w3_not_shortest']: valid = False
        
        extension = self._compute_extension(w1, w3, w5)
        truncated = bool(p5 < p3)
        
        return {'valid': valid, 'rules': rules, 'extension': extension, 'truncated': truncated}
    
    def _check_bearish(self, p):
        p0, p1, p2, p3, p4, p5 = [float(x) for x in p]
        rules = {}
        valid = True
        
        rules['w2_no_break_w1'] = bool(p2 < p0)
        if not rules['w2_no_break_w1']: valid = False
        
        rules['w3_breaks_w1'] = bool(p3 < p1)
        if not rules['w3_breaks_w1']: valid = False
        
        rules['w4_no_overlap_w1'] = bool(p4 < p1)
        if not rules['w4_no_overlap_w1']: valid = False
        
        w1, w3, w5 = p0 - p1, p2 - p3, p4 - p5
        rules['w3_not_shortest'] = bool(w3 >= min(w1, w5))
        if not rules['w3_not_shortest']: valid = False
        
        extension = self._compute_extension(w1, w3, w5)
        truncated = bool(p5 > p3)
        
        return {'valid': valid, 'rules': rules, 'extension': extension, 'truncated': truncated}
    

    def detect_double_pattern(self, impulse):
        """
        Определяет визуальный паттерн при усечении.
        Восходящий импульс -> Двойная вершина.
        Нисходящий импульс -> Двойное дно.
        """
        if not impulse.get('truncated'):
            return None
        
        direction = impulse['direction']
        
        if direction == 'bullish':
            return {
                'pattern': 'double_top',
                'description': 'Двойная вершина',
                'signal': 'bearish_reversal',
            }
        else:
            return {
                'pattern': 'double_bottom',
                'description': 'Двойное дно',
                'signal': 'bullish_reversal',
            }

    def get_last_impulse(self):
        return self.impulses[-1] if self.impulses else None

    def detect_double_pattern(self, impulse):
        """
        Определяет визуальный паттерн при усечении.
        Восходящий импульс → Двойная вершина.
        Нисходящий импульс → Двойное дно.
        """
        if not impulse.get('truncated'):
            return None
        
        direction = impulse['direction']
        
        if direction == 'bullish':
            return {
                'pattern': 'double_top',
                'description': 'Двойная вершина',
                'signal': 'bearish_reversal',
            }
        else:
            return {
                'pattern': 'double_bottom',
                'description': 'Двойное дно',
                'signal': 'bullish_reversal',
            }

