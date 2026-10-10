"""
W4W5Strategy - Стратегия W4 -> W5.

Логика:
- W4 — коррекция после W3.
- После завершения W4 ожидаем W5.
- Вход: в направлении W5.
- Цель: 100% от W3.
- Стоп: окончание W2.
"""
from .base import BaseStrategy
from fib.extension import ExtensionCalculator


class W4W5Strategy(BaseStrategy):
    """Стратегия W4 -> W5."""
    
    def __init__(self, min_w4_ratio=0.2, max_w4_ratio=0.6, target_ratio=1.000):
        super().__init__(name="W4->W5")
        self.description = "Вход после W4, цель — W5"
        self.min_w4_ratio = min_w4_ratio
        self.max_w4_ratio = max_w4_ratio
        self.target_ratio = target_ratio
        self.ext = ExtensionCalculator()
    
    def generate_signals(self, df, impulses, diagonals=None, corrections=None, combinations=None):
        trades = []
        
        if not impulses:
            return trades
        
        for imp in impulses:
            points = imp['points']
            if len(points) < 5:
                continue
            
            p0 = points[0][1]
            p1 = points[1][1]
            p2 = points[2][1]
            p3 = points[3][1]
            p4 = points[4][1]
            
            w3_len = abs(p3 - p2)
            w4_len = abs(p4 - p3)
            
            if w3_len == 0:
                continue
            
            # W4 откатила 20-60% от W3
            w4_ratio = w4_len / w3_len
            if not (self.min_w4_ratio <= w4_ratio <= self.max_w4_ratio):
                continue
            
            # Цели W5
            try:
                targets = self.ext.calculate_w5_targets(p0, p3, p4)
                if self.target_ratio not in targets['targets']:
                    continue
                target_price = targets['targets'][self.target_ratio]
            except Exception:
                continue
            
            # Стоп — окончание W2
            stop_price = p2
            
            direction = 'BUY' if imp['direction'] == 'bullish' else 'SELL'
            
            trades.append({
                'entry_time': points[4][0],
                'entry_price': p4,
                'direction': direction,
                'target': target_price,
                'stop': stop_price,
                'pattern': 'W4_completion',
                'w4_ratio': w4_ratio,
                'source': imp,
            })
        
        return trades

