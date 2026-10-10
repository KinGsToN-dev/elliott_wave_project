"""
Divergence (rules) - Дивергенция MACD/AO между волнами.

Обёртка над fib.divergence с акцентом на правила Эллиота.
"""
import pandas as pd
from fib.divergence import DivergenceDetector


class RulesDivergence:
    """Проверка дивергенции для правил Эллиота."""
    
    def __init__(self, df=None):
        self.detector = DivergenceDetector(df=df)
        self.results = []
    
    def check_impulse(self, impulse):
        """Проверка дивергенции W3/W5."""
        result = self.detector.check_w3_w5_divergence(impulse)
        return result
    
    def calculate_all(self, impulses, corrections=None):
        """Расчёт дивергенций для всех паттернов."""
        self.results = []
        
        # Импульсы
        for imp in impulses:
            result = self.check_impulse(imp)
            self.results.append({
                'pattern_id': id(imp),
                'type': 'impulse',
                'direction': imp['direction'],
                'divergence': result,
            })
        
        # Коррекции (A/C)
        if corrections:
            for corr in corrections:
                if corr['type'] in ['zigzag', 'flat']:
                    points = corr['points']
                    if len(points) >= 4:
                        a_time, a_price = points[1][0], points[1][1]
                        c_time, c_price = points[3][0], points[3][1]
                        
                        result = self.detector.check_divergence(
                            a_time, a_price, c_time, c_price
                        )
                        result['rule'] = 'A/C'
                        
                        self.results.append({
                            'pattern_id': id(corr),
                            'type': corr['type'],
                            'direction': corr['direction'],
                            'divergence': result,
                        })
        
        print(f"[OK] Дивергенция: проверено {len(self.results)} паттернов")
        return self.results
    
    def get_results(self):
        return self.results
