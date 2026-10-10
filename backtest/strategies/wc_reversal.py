"""
WCReversalStrategy - Стратегия W_C → разворот (ИНВЕРТИРОВАНО).

Логика:
- W_C — завершение коррекции (зигзаг или плоскость).
- Вход: ПО направлению коррекции (продолжение движения).
- Цель: 100% W_A.
- Стоп: начало W_C.
"""
from .base import BaseStrategy
from fib.extension import ExtensionCalculator


class WCReversalStrategy(BaseStrategy):
    """Стратегия W_C → разворот (инвертировано)."""
    
    def __init__(self):
        super().__init__(name="W_C Reversal (INV)")
        self.description = "Вход после завершения W_C (ИНВЕРТИРОВАНО)"
        self.ext = ExtensionCalculator()
    
    def generate_signals(self, df, impulses=None, diagonals=None, corrections=None, combinations=None):
        trades = []
        
        if not corrections:
            return trades
        
        for corr in corrections:
            if corr['type'] not in ['zigzag', 'flat']:
                continue
            
            points = corr['points']
            if len(points) < 4:
                continue
            
            p0 = points[0][1]  # начало
            pA = points[1][1]  # W_A
            pB = points[2][1]  # W_B
            pC = points[3][1]  # W_C
            
            # Цели W_C
            try:
                wc_type = 'flat_expanded' if corr.get('subtype') == 'expanded' else 'zigzag'
                targets = self.ext.calculate_wc_targets(p0, pA, wc_type)
                if 1.000 not in targets['targets']:
                    continue
                target_price = targets['targets'][1.000]
            except Exception:
                continue
            
            # Стоп — начало W_C (pB)
            stop_price = pB
            
            # ИНВЕРТИРОВАНО: вход ПО направлению коррекции
            if corr['direction'] == 'bearish':
                direction = 'SELL'
            else:
                direction = 'BUY'
            
            trades.append({
                'entry_time': points[3][0],  # W_C
                'entry_price': pC,
                'direction': direction,
                'target': target_price,
                'stop': stop_price,
                'pattern': f'W_C_{corr["type"]}',
                'source': corr,
            })
        
        return trades