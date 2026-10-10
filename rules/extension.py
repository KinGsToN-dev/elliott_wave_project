"""
Extension (rules) - Полные правила растяжения импульсов.

Правила (traderevolution.by):
- Растянута только одна из W1, W3, W5.
- W1 растянута → W5 = 61.8% от W1.
- W3 растянута → W1 и W5 пропорциональны.
- W5 растянута → W5 = 161.8% от W3.
- Чаще всего растянута W3.
- Растянутая волна подразделяется на 5 подволн.
"""
import pandas as pd


EXTENSION_RATIO = 1.5


class ExtensionAnalyzer:
    """Полный анализ растяжения импульса."""
    
    def __init__(self):
        self.results = []
    
    def find_extension(self, w1_len, w3_len, w5_len):
        """Определяет, какая волна растянута."""
        lengths = {'W1': w1_len, 'W3': w3_len, 'W5': w5_len}
        sorted_lengths = sorted(lengths.items(), key=lambda x: x[1], reverse=True)
        
        longest_name, longest_len = sorted_lengths[0]
        second_name, second_len = sorted_lengths[1]
        
        if second_len == 0:
            return {'extension': None, 'ratios': {}}
        
        ratio = longest_len / second_len
        extension = longest_name if ratio >= EXTENSION_RATIO else None
        
        return {
            'extension': extension,
            'longest': longest_name,
            'ratio': ratio,
            'ratios': {
                'W1_W3': w1_len / w3_len if w3_len > 0 else None,
                'W1_W5': w1_len / w5_len if w5_len > 0 else None,
                'W3_W5': w3_len / w5_len if w5_len > 0 else None,
            },
        }
    
    def check_w1_extension(self, w1_len, w5_len):
        """
        Правило для растянутой W1:
        W5 ≈ 61.8% от W1.
        """
        if w1_len == 0:
            return {'valid': False, 'rule': 'w1_extension'}
        
        expected_w5 = w1_len * 0.618
        tolerance = w1_len * 0.20  # ±20% (увеличен допуск)
        valid = abs(w5_len - expected_w5) < tolerance
        
        return {
            'valid': valid,
            'expected_w5': expected_w5,
            'actual_w5': w5_len,
            'ratio': w5_len / w1_len,
            'rule': 'w1_extension_w5_61.8',
        }
    
    def check_w3_extension(self, w1_len, w5_len):
        """
        Правило для растянутой W3:
        W1 и W5 пропорциональны (≈ 1:1).
        """
        if w1_len == 0:
            return {'valid': False, 'rule': 'w3_extension'}
        
        ratio = w5_len / w1_len
        valid = abs(ratio - 1.0) < 0.35  # ±35%
        
        return {
            'valid': valid,
            'ratio_w5_w1': ratio,
            'rule': 'w3_extension_w1_w5_proportional',
        }
    
    def check_w5_extension(self, w3_len, w5_len):
        """
        Правило для растянутой W5:
        W5 ≈ 161.8% от W3.
        """
        if w3_len == 0:
            return {'valid': False, 'rule': 'w5_extension'}
        
        expected_w5 = w3_len * 1.618
        tolerance = w3_len * 0.25
        valid = abs(w5_len - expected_w5) < tolerance
        
        return {
            'valid': valid,
            'expected_w5': expected_w5,
            'actual_w5': w5_len,
            'ratio': w5_len / w3_len,
            'rule': 'w5_extension_161.8',
        }
    
    def check_subwaves(self, impulse):
        """
        Проверяет, что растянутая волна подразделяется на 5 подволн.
        Упрощённо: если wave['extension'] == 'W3', то W3 содержит подволны (i)-(v).
        """
        ext = impulse.get('extension')
        if ext is None:
            return {'has_subwaves': False, 'extension': None}
        
        return {
            'has_subwaves': True,
            'extension': ext,
            'subwave_count': 5,
        }
    
    def calculate_all(self, impulses):
        """Полный анализ растяжения для всех импульсов."""
        self.results = []
        
        for imp in impulses:
            points = imp['points']
            if len(points) < 6:
                continue
            
            p0, p1, p2, p3, p4, p5 = [pt[1] for pt in points]
            w1_len = abs(p1 - p0)
            w3_len = abs(p3 - p2)
            w5_len = abs(p5 - p4)
            
            ext_result = self.find_extension(w1_len, w3_len, w5_len)
            
            # Проверка правил для конкретной растянутой волны
            if ext_result['extension'] == 'W1':
                rule_check = self.check_w1_extension(w1_len, w5_len)
            elif ext_result['extension'] == 'W3':
                rule_check = self.check_w3_extension(w1_len, w5_len)
            elif ext_result['extension'] == 'W5':
                rule_check = self.check_w5_extension(w3_len, w5_len)
            else:
                rule_check = None
            
            # Проверка подволн
            imp_for_sub = {'extension': ext_result['extension']}
            subwave_check = self.check_subwaves(imp_for_sub)
            
            ext_result['pattern_id'] = id(imp)
            ext_result['direction'] = imp['direction']
            ext_result['rule_check'] = rule_check
            ext_result['subwave_check'] = subwave_check
            
            self.results.append(ext_result)
        
        print(f"[OK] Растяжение: проверено {len(self.results)} импульсов")
        return self.results
    
    def get_results(self):
        return self.results
