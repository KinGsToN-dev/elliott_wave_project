"""
W2W3Strategy - Стратегия W2 → W3.

Логика:
- W2 — коррекция после W1.
- После завершения W2 ожидаем W3 (растяжение).
- Вход: в направлении W3.
- Цель: 161.8% от W1.
- Стоп: начало W1.
"""
from .base import BaseStrategy
from fib.extension import ExtensionCalculator


class W2W3Strategy(BaseStrategy):
    """Стратегия W2 → W3."""
    
    def __init__(self, min_w2_ratio=0.4, max_w2_ratio=0.85):
        super().__init__(name="W2→W3")
        self.description = "Вход после W2, цель — W3 (161.8% W1)"
        self.min_w2_ratio = min_w2_ratio
        self.max_w2_ratio = max_w2_ratio
        self.ext = ExtensionCalculator()
    
    def generate_signals(self, df, impulses, diagonals=None, corrections=None, combinations=None):
        """Генерирует сигналы на основе импульсов."""
        trades = []
        
        if not impulses:
            return trades
        
        for imp in impulses:
            points = imp['points']
            if len(points) < 3:
                continue
            
            p0 = points[0][1]  # начало W1
            p1 = points[1][1]  # конец W1
            p2 = points[2][1]  # конец W2
            
            w1_len = abs(p1 - p0)
            w2_len = abs(p2 - p1)
            
            if w1_len == 0:
                continue
            
            # Проверка: W2 откатила 40-85% от W1
            w2_ratio = w2_len / w1_len
            if not (self.min_w2_ratio <= w2_ratio <= self.max_w2_ratio):
                continue
            
            # Цели W3
            try:
                targets = self.ext.calculate_w3_targets(p0, p1, p2)
                if 1.618 not in targets['targets']:
                    continue
                target_price = targets['targets'][1.618]
            except Exception:
                continue
            
            # Стоп — начало W1
            stop_price = p0
            
            # Направление
            direction = 'BUY' if imp['direction'] == 'bullish' else 'SELL'
            
            trades.append({
                'entry_time': points[2][0],
                'entry_price': p2,
                'direction': direction,
                'target': target_price,
                'stop': stop_price,
                'pattern': 'W2_completion',
                'w2_ratio': w2_ratio,
                'source': imp,
            })
        
        return trades
