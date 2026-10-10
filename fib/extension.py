"""
Extension - Расширение Фибоначчи (цели импульсов).

Правила (traderevolution.by):
- W3: 161.8%, 200%, 261.8% от W1.
- W5: 61.8%, 78.6%, 100%, 161.8% от W3.
- W_C зигзага: 61.8%, 100%, 127.2%, 161.8% от W_A.
- W_C расширенного флэта: 161.8%.
- W_C бегущего флэта: 100%.
- W4 vs W2: 61.8%, 78.6%, 100%, 127.2%, 161.8%.
- Сужающиеся диагонали: 61.8%, 78.6%.
- Расширяющиеся диагонали: 127.2%, 161.8%.
"""
import pandas as pd


# Уровни
W3_LEVELS = [1.618, 2.000, 2.618]
W5_LEVELS = [0.618, 0.786, 1.000, 1.618]
WC_ZIGZAG_LEVELS = [0.618, 1.000, 1.272, 1.618]
WC_FLAT_EXPANDED = [1.618]
WC_FLAT_RUNNING = [1.000]
W4_VS_W2_LEVELS = [0.618, 0.786, 1.000, 1.272, 1.618]
DIAGONAL_CONTRACTING = [0.618, 0.786]
DIAGONAL_EXPANDING = [1.272, 1.618]


class ExtensionCalculator:
    """Расчёт целей расширения Фибоначчи."""
    
    def __init__(self):
        self.results = []
    
    def calculate_w3_targets(self, wave1_start, wave1_end, wave2_end):
        """Цели для W3."""
        wave1_len = abs(wave1_end - wave1_start)
        direction = 1 if wave1_end > wave1_start else -1
        
        result = {
            'wave': 'W3', 'type': 'extension_from_w1',
            'wave1_start': wave1_start, 'wave1_end': wave1_end,
            'wave1_len': wave1_len,
            'direction': 'bullish' if direction > 0 else 'bearish',
            'targets': {},
        }
        
        for lvl in W3_LEVELS:
            if direction > 0:
                result['targets'][lvl] = wave2_end + wave1_len * lvl
            else:
                result['targets'][lvl] = wave2_end - wave1_len * lvl
        
        return result
    
    def calculate_w5_targets(self, wave1_start, wave3_end, wave4_end):
        """Цели для W5."""
        wave1_to_3_len = abs(wave3_end - wave1_start)
        direction = 1 if wave3_end > wave1_start else -1
        
        result = {
            'wave': 'W5', 'type': 'extension_from_w3',
            'wave1_start': wave1_start, 'wave3_end': wave3_end,
            'wave1_to_3_len': wave1_to_3_len,
            'direction': 'bullish' if direction > 0 else 'bearish',
            'targets': {},
        }
        
        for lvl in W5_LEVELS:
            if direction > 0:
                result['targets'][lvl] = wave4_end + wave1_to_3_len * lvl
            else:
                result['targets'][lvl] = wave4_end - wave1_to_3_len * lvl
        
        return result
    
    def calculate_wc_targets(self, wave_a_start, wave_a_end, wc_type='zigzag'):
        """Цели для W_C."""
        wave_a_len = abs(wave_a_end - wave_a_start)
        direction = 1 if wave_a_end > wave_a_start else -1
        
        if wc_type == 'flat_expanded':
            levels = WC_FLAT_EXPANDED
        elif wc_type == 'flat_running':
            levels = WC_FLAT_RUNNING
        else:
            levels = WC_ZIGZAG_LEVELS
        
        result = {
            'wave': 'W_C', 'type': wc_type,
            'wave_a_start': wave_a_start, 'wave_a_end': wave_a_end,
            'wave_a_len': wave_a_len,
            'direction': 'bullish' if direction > 0 else 'bearish',
            'targets': {},
        }
        
        for lvl in levels:
            if direction > 0:
                result['targets'][lvl] = wave_a_start + wave_a_len * lvl
            else:
                result['targets'][lvl] = wave_a_start - wave_a_len * lvl
        
        return result
    
    def calculate_w4_vs_w2(self, w2_start, w2_end, w4_start):
        """
        Расширение W4 относительно W2.
        Уровни: 61.8%, 78.6%, 100%, 127.2%, 161.8% от W2.
        
        Args:
            w2_start: начало W2
            w2_end: окончание W2 (пик/дно)
            w4_start: начало W4 (окончание W3)
        """
        w2_len = abs(w2_end - w2_start)
        direction = 1 if w2_end > w2_start else -1
        
        result = {
            'wave': 'W4', 'type': 'extension_from_w2',
            'w2_start': w2_start, 'w2_end': w2_end,
            'w2_len': w2_len,
            'direction': 'bullish' if direction > 0 else 'bearish',
            'targets': {},
        }
        
        # W4 = расширение W2 от начала W4
        for lvl in W4_VS_W2_LEVELS:
            if direction > 0:
                result['targets'][lvl] = w4_start + w2_len * lvl
            else:
                result['targets'][lvl] = w4_start - w2_len * lvl
        
        return result
    
    def calculate_diagonal_targets(self, w1_start, w1_end, w2_end, diag_type='contracting'):
        """
        Расширение для диагоналей.
        
        Args:
            w1_start, w1_end: W1
            w2_end: окончание W2
            diag_type: 'contracting' или 'expanding'
        """
        w1_len = abs(w1_end - w1_start)
        direction = 1 if w1_end > w1_start else -1
        
        if diag_type == 'contracting':
            levels = DIAGONAL_CONTRACTING
        else:
            levels = DIAGONAL_EXPANDING
        
        result = {
            'wave': 'W3_diag', 'type': f'diagonal_{diag_type}',
            'w1_start': w1_start, 'w1_end': w1_end,
            'w1_len': w1_len,
            'direction': 'bullish' if direction > 0 else 'bearish',
            'targets': {},
        }
        
        for lvl in levels:
            if direction > 0:
                result['targets'][lvl] = w2_end + w1_len * lvl
            else:
                result['targets'][lvl] = w2_end - w1_len * lvl
        
        return result
    
    def calculate_all(self, impulses, corrections):
        """Расчёт целей для всех паттернов."""
        self.results = []
        
        for imp in impulses:
            points = imp['points']
            p0, p1, p2, p3, p4, p5 = [pt[1] for pt in points]
            
            self.results.append({
                'pattern_id': id(imp),
                'direction': imp['direction'],
                'w3': self.calculate_w3_targets(p0, p1, p2),
                'w5': self.calculate_w5_targets(p0, p3, p4),
                'w4_vs_w2': self.calculate_w4_vs_w2(p1, p2, p3),
            })
        
        for corr in corrections:
            if corr['type'] == 'zigzag':
                points = corr['points']
                p0, pA, pB, pC = [pt[1] for pt in points]
                self.results.append({
                    'pattern_id': id(corr),
                    'direction': corr['direction'],
                    'wc': self.calculate_wc_targets(p0, pA, 'zigzag'),
                })
            elif corr['type'] == 'flat':
                points = corr['points']
                p0, pA, pB, pC = [pt[1] for pt in points]
                subtype = corr.get('subtype', 'regular')
                wc_type = 'flat_expanded' if subtype == 'expanded' else 'flat_running' if subtype == 'running' else 'flat_expanded'
                self.results.append({
                    'pattern_id': id(corr),
                    'direction': corr['direction'],
                    'wc': self.calculate_wc_targets(p0, pA, wc_type),
                })
        
        return self.results
    
    def get_last_results(self):
        return self.results
