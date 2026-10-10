"""
Proportions - Пропорциональность волн Эллиота.

Правила (traderevolution.by):
- W1 и W3 импульса — пропорциональны.
- W1 и W5 импульса — пропорциональны.
- A и C зигзага/плоскости — эквивалентны (обычно 1:1).
- W и Y двойного зигзага — эквивалентны.
- W4 может равняться 61.8%, 78.6%, 100%, 127.2%, 161.8% от W2.
"""
import pandas as pd


# Стандартные соотношения
PROP_RATIOS = [0.618, 0.786, 1.000, 1.272, 1.618]

# Допуск для «эквивалентности» (5%)
EQUIVALENCE_TOLERANCE = 0.05


class ProportionsCalculator:
    """Проверка пропорциональности волн."""
    
    def __init__(self):
        self.results = []
    
    def check_w1_w3(self, w1_len, w3_len):
        """
        Проверяет соотношение W1 и W3.
        
        Args:
            w1_len: длина W1
            w3_len: длина W3
        
        Returns:
            dict с ratio и conclusion
        """
        if w1_len == 0:
            return {'ratio': None, 'proportional': False}
        
        ratio = w3_len / w1_len
        # Проверяем, попадает ли в стандартные уровни (±5%)
        proportional = any(
            abs(ratio - r) < EQUIVALENCE_TOLERANCE * r for r in PROP_RATIOS
        )
        
        return {
            'ratio': ratio,
            'proportional': proportional,
            'closest_ratio': min(PROP_RATIOS, key=lambda r: abs(ratio - r)),
            'rule': 'W1/W3',
        }
    
    def check_w1_w5(self, w1_len, w5_len):
        """Проверяет соотношение W1 и W5."""
        if w1_len == 0:
            return {'ratio': None, 'proportional': False}
        
        ratio = w5_len / w1_len
        proportional = any(
            abs(ratio - r) < EQUIVALENCE_TOLERANCE * r for r in PROP_RATIOS
        )
        
        return {
            'ratio': ratio,
            'proportional': proportional,
            'closest_ratio': min(PROP_RATIOS, key=lambda r: abs(ratio - r)),
            'rule': 'W1/W5',
        }
    
    def check_w4_vs_w2(self, w2_len, w4_len):
        """
        Проверяет соотношение W4 к W2.
        W4 = 61.8%, 78.6%, 100%, 127.2%, 161.8% от W2.
        """
        if w2_len == 0:
            return {'ratio': None, 'proportional': False}
        
        ratio = w4_len / w2_len
        proportional = any(
            abs(ratio - r) < EQUIVALENCE_TOLERANCE * r for r in PROP_RATIOS
        )
        
        return {
            'ratio': ratio,
            'proportional': proportional,
            'closest_ratio': min(PROP_RATIOS, key=lambda r: abs(ratio - r)),
            'rule': 'W4/W2',
        }
    
    def check_a_c(self, a_len, c_len):
        """
        Проверяет эквивалентность A и C (зигзаг/плоскость).
        Обычно 1:1.
        """
        if a_len == 0:
            return {'ratio': None, 'equivalent': False}
        
        ratio = c_len / a_len
        equivalent = abs(ratio - 1.0) < EQUIVALENCE_TOLERANCE
        
        return {
            'ratio': ratio,
            'equivalent': equivalent,
            'rule': 'A/C',
        }
    
    def check_w_y(self, w_len, y_len):
        """Проверяет эквивалентность W и Y (двойной зигзаг)."""
        if w_len == 0:
            return {'ratio': None, 'equivalent': False}
        
        ratio = y_len / w_len
        equivalent = abs(ratio - 1.0) < EQUIVALENCE_TOLERANCE
        
        return {
            'ratio': ratio,
            'equivalent': equivalent,
            'rule': 'W/Y',
        }
    

    def check_triangle_alternation(self, wa, wc, we, triangle_type='contracting'):
        """
        Пропорциональность чередующихся волн в треугольнике (A -> C -> E).
        Сужающиеся: 61.8%, 78.6%.
        Расширяющиеся: 127.2%, 161.8%.
        """
        if wa == 0 or wc == 0:
            return {'valid': False, 'rule': 'triangle_alternation'}
        
        if triangle_type == 'contracting':
            levels = [0.618, 0.786]
        else:
            levels = [1.272, 1.618]
        
        ratio_c_a = wc / wa
        ratio_e_c = we / wc if wc > 0 else 0
        
        valid_c = any(abs(ratio_c_a - l) < 0.15 for l in levels)
        valid_e = any(abs(ratio_e_c - l) < 0.15 for l in levels) if wc > 0 else False
        
        return {
            'valid': valid_c or valid_e,
            'ratio_c_a': ratio_c_a,
            'ratio_e_c': ratio_e_c,
            'expected_levels': levels,
            'rule': 'triangle_alternation',
        }

    def calculate_all(self, impulses, corrections):
        """Расчёт пропорций для всех паттернов."""
        self.results = []
        
        # Для импульсов
        for imp in impulses:
            points = imp['points']
            p0, p1, p2, p3, p4, p5 = [pt[1] for pt in points]
            
            w1_len = abs(p1 - p0)
            w2_len = abs(p2 - p1)
            w3_len = abs(p3 - p2)
            w4_len = abs(p4 - p3)
            w5_len = abs(p5 - p4)
            
            self.results.append({
                'pattern_id': id(imp),
                'type': 'impulse',
                'direction': imp['direction'],
                'w1_w3': self.check_w1_w3(w1_len, w3_len),
                'w1_w5': self.check_w1_w5(w1_len, w5_len),
                'w4_w2': self.check_w4_vs_w2(w2_len, w4_len),
            })
        
        # Для зигзагов
        for corr in corrections:
            if corr['type'] == 'zigzag':
                points = corr['points']
                p0, pA, pB, pC = [pt[1] for pt in points]
                a_len = abs(pA - p0)
                c_len = abs(pC - pB)
                
                self.results.append({
                    'pattern_id': id(corr),
                    'type': 'zigzag',
                    'direction': corr['direction'],
                    'a_c': self.check_a_c(a_len, c_len),
                })
            
            # Для плоскостей
            elif corr['type'] == 'flat':
                points = corr['points']
                p0, pA, pB, pC = [pt[1] for pt in points]
                a_len = abs(pA - p0)
                c_len = abs(pC - pB)
                
                self.results.append({
                    'pattern_id': id(corr),
                    'type': 'flat',
                    'direction': corr['direction'],
                    'a_c': self.check_a_c(a_len, c_len),
                })
        
        return self.results
    
    def get_results(self):
        return self.results

