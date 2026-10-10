"""
Alternation - Правило чередования W2/W4.

Правила (traderevolution.by):
- Если W2 глубокая (зигзаг) -> W4 плоская (плоскость/треугольник).
- Если W2 плоская -> W4 глубокая.
- W4 может быть флэтом, треугольником или комбинацией.
- W2 чаще всего зигзаг или комбинация зигзагов.
- В диагоналях чередования НЕТ.
"""
import pandas as pd


# Пороги для классификации
DEEP_THRESHOLD = 0.500      # > 50% откат = глубокая
FLAT_THRESHOLD = 0.382      # < 38.2% откат = плоская


class AlternationChecker:
    """Проверка правила чередования W2/W4."""
    
    def __init__(self):
        self.results = []
    
    def classify_w2(self, w2_retracement_ratio):
        """
        Классифицирует W2 по глубине отката.
        
        Args:
            w2_retracement_ratio: доля отката W2 от W1 (0.0 - 1.0)
        
        Returns:
            'deep' / 'flat' / 'neutral'
        """
        if w2_retracement_ratio > DEEP_THRESHOLD:
            return 'deep'
        elif w2_retracement_ratio < FLAT_THRESHOLD:
            return 'flat'
        return 'neutral'
    
    def classify_w4(self, w4_retracement_ratio):
        """Классифицирует W4 по глубине отката."""
        if w4_retracement_ratio > DEEP_THRESHOLD:
            return 'deep'
        elif w4_retracement_ratio < FLAT_THRESHOLD:
            return 'flat'
        return 'neutral'
    
    def check_alternation(self, w2_ratio, w4_ratio, is_diagonal=False):
        """
        Проверяет чередование W2 и W4.
        
        Args:
            w2_ratio: доля отката W2
            w4_ratio: доля отката W4
            is_diagonal: если True — чередования нет
        
        Returns:
            dict с результатом
        """
        if is_diagonal:
            return {
                'valid': True,
                'rule': 'no_alternation_in_diagonal',
                'w2_type': self.classify_w2(w2_ratio),
                'w4_type': self.classify_w4(w4_ratio),
            }
        
        w2_type = self.classify_w2(w2_ratio)
        w4_type = self.classify_w4(w4_ratio)
        
        # Чередование: разные типы
        alternation_ok = False
        if w2_type == 'deep' and w4_type == 'flat':
            alternation_ok = True
        elif w2_type == 'flat' and w4_type == 'deep':
            alternation_ok = True
        elif w2_type == 'neutral' or w4_type == 'neutral':
            alternation_ok = True  # нейтральные — допустимо
        
        return {
            'valid': alternation_ok,
            'w2_type': w2_type,
            'w4_type': w4_type,
            'w2_ratio': w2_ratio,
            'w4_ratio': w4_ratio,
            'rule': 'alternation',
        }

    def check_abc_alternation(self, a_ratio, b_ratio):
        """
        Чередование A-B в зигзаге.
        A глубокая -> B плоская, и наоборот.
        """
        a_type = self.classify_w2(a_ratio)
        b_type = self.classify_w4(b_ratio)
        
        valid = False
        if a_type == 'deep' and b_type == 'flat':
            valid = True
        elif a_type == 'flat' and b_type == 'deep':
            valid = True
        elif a_type == 'neutral' or b_type == 'neutral':
            valid = True
        
        return {
            'valid': valid,
            'a_type': a_type,
            'b_type': b_type,
            'rule': 'abc_alternation',
        }
    
    def calculate_all(self, impulses):
        """Расчёт чередования для всех импульсов."""
        self.results = []
        
        for imp in impulses:
            points = imp['points']
            if len(points) < 6:
                continue
            
            p0, p1, p2, p3, p4, p5 = [pt[1] for pt in points]
            
            # W1_len, W2_len, W3_len, W4_len
            w1_len = abs(p1 - p0)
            w2_len = abs(p2 - p1)
            w3_len = abs(p3 - p2)
            w4_len = abs(p4 - p3)
            
            if w1_len == 0 or w3_len == 0:
                continue
            
            w2_ratio = w2_len / w1_len  # доля отката W2 от W1
            w4_ratio = w4_len / w3_len  # доля отката W4 от W3
            
            result = self.check_alternation(w2_ratio, w4_ratio)
            result['pattern_id'] = id(imp)
            result['direction'] = imp['direction']
            self.results.append(result)
        
        print(f"[OK] Чередование: проверено {len(self.results)} импульсов")
        return self.results
    
    def get_results(self):
        return self.results

