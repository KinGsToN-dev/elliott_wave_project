"""
Retracement - Сетка коррекции Фибоначчи.

Правила (traderevolution.by):
- W2 (глубокая): 50%, 61.8%, 78.6% от W1.
- W2 (плоская):  23.6%, 38.2%, 50% от W1.
- W4: 38.2%, 50% от W3.
- W_B зигзага: 50%, 61.8% от W_A.
- W_B плоскости: ≥ 90% от W_A.
"""
import pandas as pd


# Стандартные уровни Фибоначчи
FIB_LEVELS = [0.236, 0.382, 0.500, 0.618, 0.786, 0.900]

# Специфичные для волн
DEEP_LEVELS = [0.500, 0.618, 0.786]     # для глубоких W2 (зигзаг)
FLAT_LEVELS = [0.236, 0.382, 0.500]     # для плоских W2 (плоскость)
W4_LEVELS   = [0.382, 0.500]            # для W4
WB_LEVELS   = [0.500, 0.618, 0.900]     # для W_B зигзага/плоскости


class RetracementCalculator:
    """Расчёт уровней коррекции Фибоначчи."""
    
    def __init__(self):
        self.results = []
    
    def calculate_w2_levels(self, wave1_start, wave1_end, w2_type='deep'):
        """
        Уровни для W2 (откат от W1).
        
        Args:
            wave1_start: цена начала W1
            wave1_end: цена окончания W1
            w2_type: 'deep' (зигзаг) или 'flat' (плоскость)
        
        Returns:
            dict с уровнями и метаданными
        """
        wave1_len = wave1_end - wave1_start
        levels = DEEP_LEVELS if w2_type == 'deep' else FLAT_LEVELS
        
        result = {
            'wave': 'W2',
            'type': w2_type,
            'wave1_start': wave1_start,
            'wave1_end': wave1_end,
            'wave1_len': wave1_len,
            'levels': {},
        }
        
        for lvl in levels:
            result['levels'][lvl] = wave1_end - wave1_len * lvl
        
        return result
    
    def calculate_w4_levels(self, wave3_start, wave3_end):
        """
        Уровни для W4 (откат от W3).
        
        Args:
            wave3_start: цена начала W3
            wave3_end: цена окончания W3
        
        Returns:
            dict с уровнями
        """
        wave3_len = wave3_end - wave3_start
        
        result = {
            'wave': 'W4',
            'type': 'standard',
            'wave3_start': wave3_start,
            'wave3_end': wave3_end,
            'wave3_len': wave3_len,
            'levels': {},
        }
        
        for lvl in W4_LEVELS:
            result['levels'][lvl] = wave3_end - wave3_len * lvl
        
        return result
    
    def calculate_wb_levels(self, wave_a_start, wave_a_end, wb_type='zigzag'):
        """
        Уровни для W_B (откат от W_A).
        
        Args:
            wave_a_start: цена начала W_A
            wave_a_end: цена окончания W_A
            wb_type: 'zigzag' или 'flat'
        
        Returns:
            dict с уровнями
        """
        wave_a_len = wave_a_end - wave_a_start
        
        result = {
            'wave': 'W_B',
            'type': wb_type,
            'wave_a_start': wave_a_start,
            'wave_a_end': wave_a_end,
            'wave_a_len': wave_a_len,
            'levels': {},
        }
        
        if wb_type == 'flat':
            # Плоскость: откат ≥ 90%
            result['levels'][0.900] = wave_a_end - wave_a_len * 0.900
            result['levels'][1.000] = wave_a_end - wave_a_len * 1.000
            result['levels'][1.236] = wave_a_end - wave_a_len * 1.236
        else:
            # Зигзаг: 50%, 61.8%, 78.6%
            for lvl in WB_LEVELS:
                result['levels'][lvl] = wave_a_end - wave_a_len * lvl
        
        return result
    
    def calculate_all(self, impulses, corrections):
        """
        Рассчитывает уровни для всех найденных импульсов и коррекций.
        
        Args:
            impulses: список импульсов (из ImpulseDetector)
            corrections: список коррекций (из CorrectionDetector)
        
        Returns:
            список результатов
        """
        self.results = []
        
        # Для каждого импульса — W2 и W4
        for imp in impulses:
            points = imp['points']
            # points = [(t0, p0, '0'), (t1, p1, '1'), ..., (t5, p5, '5')]
            p0, p1, p2, p3, p4, p5 = [pt[1] for pt in points]
            
            # W2 — откат от W1 (p0 -> p1)
            w2_type = 'deep' if imp.get('direction') == 'bullish' else 'deep'
            self.results.append({
                'pattern_id': id(imp),
                'direction': imp['direction'],
                'w2': self.calculate_w2_levels(p0, p1, w2_type),
                'w4': self.calculate_w4_levels(p2, p3),
            })
        
        # Для каждой коррекции-зигзага — W_B
        for corr in corrections:
            if corr['type'] == 'zigzag':
                points = corr['points']
                # points = [(t0, p0, '0'), (t1, pA, 'A'), (t2, pB, 'B'), (t3, pC, 'C')]
                p0, pA, pB, pC = [pt[1] for pt in points]
                self.results.append({
                    'pattern_id': id(corr),
                    'direction': corr['direction'],
                    'wb': self.calculate_wb_levels(p0, pA, 'zigzag'),
                })
            elif corr['type'] == 'flat':
                points = corr['points']
                p0, pA, pB, pC = [pt[1] for pt in points]
                self.results.append({
                    'pattern_id': id(corr),
                    'direction': corr['direction'],
                    'wb': self.calculate_wb_levels(p0, pA, 'flat'),
                })
        
        return self.results
    
    def get_last_results(self):
        return self.results

