"""
Diagonal - Детекция диагональных треугольников.
Добавлено: выброс/недобой W5 относительно линии 1-3.
"""
import pandas as pd
import numpy as np


class DiagonalDetector:
    def __init__(self, pivots, df=None, min_atr_ratio=1.5):
        self.pivots = pivots
        self.df = df
        self.min_atr_ratio = min_atr_ratio
        self.diagonals = []
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
    
    def check_throw_over(self, p1, p3, p5, shape):
        """
        Проверка выброса (throw over) или недобоя (shortfall).
        Линия 1-3 -> W5 относительно неё.
        """
        slope = (p3 - p1) / 2.0
        expected_w5 = p3 + slope * 2
        
        diff = p5 - expected_w5
        tolerance = abs(slope) * 0.5 if slope != 0 else 0.0001
        
        result = {
            'expected_w5': expected_w5,
            'actual_w5': p5,
            'diff': diff,
            'tolerance': tolerance,
            'shape': shape,
        }
        
        if shape == 'contracting':
            result['is_throw_over'] = bool(abs(diff) > tolerance)
            result['is_shortfall'] = False
        elif shape == 'expanding':
            result['is_shortfall'] = bool(abs(diff) > tolerance)
            result['is_throw_over'] = False
        else:
            result['is_throw_over'] = False
            result['is_shortfall'] = False
        
        return result
    
    def find_diagonals(self):
        if self.pivots is None or len(self.pivots) < 6:
            print("[WARNING] Недостаточно пивотов для поиска диагоналей.")
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
            
            size = abs(p[5] - p[0])
            if self.atr is not None and self.atr > 0:
                if size < self.min_atr_ratio * self.atr:
                    continue
            
            if is_bullish:
                result = self._check_bullish(p)
            else:
                result = self._check_bearish(p)
            
            if not result['valid']:
                continue
            
            diagonal = {
                'start_idx': i,
                'start_time': times[i],
                'end_time': times[i + 5],
                'direction': 'bullish' if is_bullish else 'bearish',
                'type': result['type'],
                'shape': result['shape'],
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
                'size': size,
                'truncated': bool(result['truncated']),
                'rules': result['rules'],
                'is_throw_over': result.get('throw_over', {}).get('is_throw_over', False),
                'is_shortfall': result.get('throw_over', {}).get('is_shortfall', False),
            }
            self.diagonals.append(diagonal)
        
        self.diagonals = self._filter_overlaps(self.diagonals)
        print(f"[OK] Найдено диагоналей: {len(self.diagonals)}")
        return self.diagonals
    
    def _filter_overlaps(self, diagonals):
        if not diagonals:
            return []
        sorted_d = sorted(diagonals, key=lambda x: x['size'], reverse=True)
        filtered = []
        for d in sorted_d:
            overlap = False
            for existing in filtered:
                if (d['start_time'] < existing['end_time'] and 
                    d['end_time'] > existing['start_time']):
                    overlap = True
                    break
            if not overlap:
                filtered.append(d)
        filtered.sort(key=lambda x: x['start_time'])
        return filtered
    
    def _classify_shape(self, w1, w3, w5, w2, w4):
        contracting = (w1 > w3 > w5) and (w2 > w4)
        expanding = (w1 < w3 < w5) and (w2 < w4)
        
        if contracting:
            return 'contracting'
        elif expanding:
            return 'expanding'
        return None
    
    def _check_bullish(self, p):
        p0, p1, p2, p3, p4, p5 = [float(x) for x in p]
        rules = {}
        valid = True
        
        rules['w2_no_break_w1'] = bool(p2 > p0)
        if not rules['w2_no_break_w1']: valid = False
        
        rules['w3_breaks_w1'] = bool(p3 > p1)
        if not rules['w3_breaks_w1']: valid = False
        
        rules['w4_overlaps_w1'] = bool(p4 < p1)
        if not rules['w4_overlaps_w1']: valid = False
        
        rules['w4_no_break_w2'] = bool(p4 > p2)
        if not rules['w4_no_break_w2']: valid = False
        
        w1 = p1 - p0
        w3 = p3 - p2
        w5 = p5 - p4
        rules['w3_not_shortest'] = bool(w3 >= min(w1, w5))
        if not rules['w3_not_shortest']: valid = False
        
        w2_len = abs(p2 - p1)
        w4_len = abs(p4 - p3)
        shape = self._classify_shape(w1, w3, w5, w2_len, w4_len)
        if shape is None:
            shape = 'unknown'
        
        throw_over = self.check_throw_over(p1, p3, p5, shape)
        truncated = bool(p5 < p3)
        
        return {
            'valid': valid, 'rules': rules, 'shape': shape,
            'type': 'auto', 'truncated': truncated, 'throw_over': throw_over,
        }
    
    def _check_bearish(self, p):
        p0, p1, p2, p3, p4, p5 = [float(x) for x in p]
        rules = {}
        valid = True
        
        rules['w2_no_break_w1'] = bool(p2 < p0)
        if not rules['w2_no_break_w1']: valid = False
        
        rules['w3_breaks_w1'] = bool(p3 < p1)
        if not rules['w3_breaks_w1']: valid = False
        
        rules['w4_overlaps_w1'] = bool(p4 > p1)
        if not rules['w4_overlaps_w1']: valid = False
        
        rules['w4_no_break_w2'] = bool(p4 < p2)
        if not rules['w4_no_break_w2']: valid = False
        
        w1 = p0 - p1
        w3 = p2 - p3
        w5 = p4 - p5
        rules['w3_not_shortest'] = bool(w3 >= min(w1, w5))
        if not rules['w3_not_shortest']: valid = False
        
        w2_len = abs(p2 - p1)
        w4_len = abs(p4 - p3)
        shape = self._classify_shape(w1, w3, w5, w2_len, w4_len)
        if shape is None:
            shape = 'unknown'
        
        throw_over = self.check_throw_over(p1, p3, p5, shape)
        truncated = bool(p5 > p3)
        
        return {
            'valid': valid, 'rules': rules, 'shape': shape,
            'type': 'auto', 'truncated': truncated, 'throw_over': throw_over,
        }
    
    def get_last_diagonal(self):
        return self.diagonals[-1] if self.diagonals else None

