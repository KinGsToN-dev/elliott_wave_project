"""
Correction - Детекция коррекционных паттернов.
Типы: зигзаг, двойной зигзаг, плоскость (3 типа), треугольник (3 типа), комбинации.

Правила (traderevolution.by):
- Зигзаг (5-3-5): W_B не заходит за начало W_A; W_C < W_A.
- Двойной зигзаг (3-3-3): W_X не заходит за начало W_W.
- Плоскость (3-3-5):
  - Обычная: W_B ≈ 90% W_A, W_C ≈ W_A.
  - Расширенная: W_B > W_A, W_C > W_A.
  - Бегущая: W_B > W_A, W_C < W_A (усечение).
- Треугольник (3-3-3-3-3):
  - Симметричный: C < A, D < B, E < C.
  - Восходящий: D на уровне B.
  - Расширяющийся: C > A, D > B, E > C.
"""
import pandas as pd
import numpy as np


class CorrectionDetector:
    def __init__(self, pivots, df=None, min_atr_ratio=1.0):
        self.pivots = pivots
        self.df = df
        self.min_atr_ratio = min_atr_ratio
        self.corrections = []
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
    
    def find_corrections(self):
        """Поиск всех типов коррекций."""
        if self.pivots is None or len(self.pivots) < 4:
            print("[WARNING] Недостаточно пивотов для поиска коррекций.")
            return []
        
        print(f"\n[INFO] Поиск зигзагов и плоскостей (3 точки)...")
        self._find_zigzags_and_flats()
        
        print(f"[INFO] Поиск треугольников (5 точек)...")
        self._find_triangles()
        
        self.corrections = self._filter_overlaps(self.corrections)
        print(f"[OK] Найдено коррекций: {len(self.corrections)}")
        return self.corrections
    
    def _find_zigzags_and_flats(self):
        """Поиск ABC-структур (зигзаги, плоскости)."""
        prices = self.pivots['price'].values
        types = self.pivots['type'].values
        times = self.pivots.index
        
        # Минимум 4 точки: 0-A-B-C (3 ноги)
        for i in range(len(prices) - 3):
            p = prices[i:i+4]
            t = types[i:i+4]
            
            is_bullish = (t[0] == 'high' and t[1] == 'low' and t[2] == 'high' and t[3] == 'low')
            is_bearish = (t[0] == 'low' and t[1] == 'high' and t[2] == 'low' and t[3] == 'high')
            
            if not (is_bullish or is_bearish):
                continue
            
            size = abs(p[3] - p[0])
            if self.atr is not None and self.atr > 0:
                if size < self.min_atr_ratio * self.atr:
                    continue
            
            if is_bullish:
                result = self._classify_abc_bearish(p)
            else:
                result = self._classify_abc_bullish(p)
            
            if result['valid']:
                self.corrections.append({
                    'start_idx': i,
                    'start_time': times[i],
                    'end_time': times[i + 3],
                    'direction': 'bullish' if is_bullish else 'bearish',
                    'type': result['type'],
                    'subtype': result['subtype'],
                    'points': [
                        (times[i],     p[0], '0'),
                        (times[i + 1], p[1], 'A'),
                        (times[i + 2], p[2], 'B'),
                        (times[i + 3], p[3], 'C'),
                    ],
                    'size': size,
                    'rules': result['rules'],
                })
    
    def _find_triangles(self):
        """Поиск треугольников A-B-C-D-E (5 точек)."""
        prices = self.pivots['price'].values
        types = self.pivots['type'].values
        times = self.pivots.index
        
        for i in range(len(prices) - 5):
            p = prices[i:i+6]
            t = types[i:i+6]
            
            # Треугольник: чередование high/low
            is_contracting = (t[0] == 'high' and t[5] == 'low')
            is_expanding = (t[0] == 'low' and t[5] == 'high')
            
            if not (is_contracting or is_expanding):
                continue
            
            size = abs(p[5] - p[0])
            if self.atr is not None and self.atr > 0:
                if size < self.min_atr_ratio * self.atr:
                    continue
            
            result = self._classify_triangle(p)
            
            if result['valid']:
                self.corrections.append({
                    'start_idx': i,
                    'start_time': times[i],
                    'end_time': times[i + 5],
                    'direction': 'neutral',
                    'type': 'triangle',
                    'subtype': result['subtype'],
                    'points': [
                        (times[i],     p[0], '0'),
                        (times[i + 1], p[1], 'A'),
                        (times[i + 2], p[2], 'B'),
                        (times[i + 3], p[3], 'C'),
                        (times[i + 4], p[4], 'D'),
                        (times[i + 5], p[5], 'E'),
                    ],
                    'size': size,
                    'rules': result['rules'],
                })
    
    def _classify_abc_bullish(self, p):
        """
        Классификация ABC для случая: p0=low, p1=high, p2=low, p3=high.
        (коррекция вниз — идёт от high к low, но структура обратная)
        """
        # Здесь p1 = вершина (начало коррекции), p3 = конец коррекции
        # W_A = p0→p1 (вверх), W_B = p1→p2 (вниз), W_C = p2→p3 (вверх)
        # Это НЕ коррекция, а движение по тренду. Пропускаем.
        return {'valid': False}
    
    def _classify_abc_bearish(self, p):
        """
        Классификация ABC для случая: p0=high, p1=low, p2=high, p3=low.
        Коррекция вверх внутри нисходящего тренда.
        W_A = p0→p1 (вниз), W_B = p1→p2 (вверх), W_C = p2→p3 (вниз).
        """
        p0, p1, p2, p3 = [float(x) for x in p]
        
        w_a = abs(p1 - p0)  # длина A
        w_b = abs(p2 - p1)  # длина B
        w_c = abs(p3 - p2)  # длина C
        
        if w_a == 0 or w_b == 0:
            return {'valid': False}
        
        rules = {}
        
        # Правило зигзага: W_B не заходит за начало W_A (p2 < p0)
        zigzag_ok = bool(p2 < p0)
        rules['w_b_no_break_w_a'] = zigzag_ok
        
        # Правило зигзага: W_C < W_A по цене (p3 < p1)
        zigzag_c_lower = bool(p3 < p1)
        rules['w_c_lower_than_a'] = zigzag_c_lower
        
        # Определяем тип
        if zigzag_ok and zigzag_c_lower:
            # Это зигзаг
            return {
                'valid': True,
                'type': 'zigzag',
                'subtype': 'regular',
                'rules': rules,
            }
        
        # Плоскость: W_B заходит за начало W_A (p2 > p0)
        if not zigzag_ok:
            # Проверяем расширенную или бегущую
            expanded = bool(p3 < p1)  # C пробивает A
            running = bool(p3 > p1)   # C не пробивает A
            
            if expanded:
                return {
                    'valid': True,
                    'type': 'flat',
                    'subtype': 'expanded',
                    'rules': rules,
                }
            elif running:
                return {
                    'valid': True,
                    'type': 'flat',
                    'subtype': 'running',
                    'rules': rules,
                }
            else:
                return {
                    'valid': True,
                    'type': 'flat',
                    'subtype': 'regular',
                    'rules': rules,
                }
        
        return {'valid': False}
    
   # Замените метод _classify_triangle на этот:

    def _classify_triangle(self, p):
        """
        Классификация треугольника A-B-C-D-E.
        Ослабленные условия с допусками.
        """
        p0, pA, pB, pC, pD, pE = [float(x) for x in p]
        
        wA = abs(pA - p0)
        wB = abs(pB - pA)
        wC = abs(pC - pB)
        wD = abs(pD - pC)
        wE = abs(pE - pD)
        
        if any(w == 0 for w in [wA, wB, wC, wD, wE]):
            return {'valid': False}
        
        rules = {}
        
        # Симметричный: C < A, D < B, E < C (с допуском 5%)
        symmetric = (wC < wA * 1.05) and (wD < wB * 1.05) and (wE < wC * 1.05)
        
        # Восходящий: D на уровне B (допуск 20%), E > C
        d_b_close = abs(pD - pB) < (abs(pB - pA) * 0.2 + 0.0005)
        ascending = d_b_close and (pE > pC)
        
        # Расширяющийся: C > A, D > B, E > C (с допуском 5%)
        expanding = (wC > wA * 0.95) and (wD > wB * 0.95) and (wE > wC * 0.95)
        
        rules['symmetric'] = symmetric
        rules['ascending'] = ascending
        rules['expanding'] = expanding
        
        # Приоритет: сначала явные случаи
        if expanding and not symmetric:
            return {'valid': True, 'subtype': 'expanding', 'rules': rules}
        elif ascending:
            return {'valid': True, 'subtype': 'ascending', 'rules': rules}
        elif symmetric:
            return {'valid': True, 'subtype': 'symmetric', 'rules': rules}
        elif expanding:
            return {'valid': True, 'subtype': 'expanding', 'rules': rules}
        
        return {'valid': False}
     
    def _filter_overlaps(self, corrections):
        if not corrections:
            return []
        sorted_c = sorted(corrections, key=lambda x: x['size'], reverse=True)
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
    
    def get_last_correction(self):
        return self.corrections[-1] if self.corrections else None
