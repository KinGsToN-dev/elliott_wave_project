"""
W5DivergenceStrategy - Стратегия W5 + дивергенция → разворот.

Логика:
- Импульс завершён.
- Дивергенция MACD между W3 и W5.
- Вход: против направления импульса.
- Цель: 38.2% откат от W1-W5.
- Стоп: окончание W5.
"""
from .base import BaseStrategy
from fib.divergence import DivergenceDetector


class W5DivergenceStrategy(BaseStrategy):
    """Стратегия W5 + дивергенция."""
    
    def __init__(self, df=None):
        super().__init__(name="W5+Divergence")
        self.description = "Вход после W5 с дивергенцией MACD"
        self.divergence = DivergenceDetector(df=df)
        self.min_retracement = 0.382
    
    def generate_signals(self, df, impulses=None, diagonals=None, corrections=None, combinations=None):
        trades = []
        
        if not impulses:
            return trades
        
        # Если у детектора нет df — обновляем
        if self.divergence.df is None:
            self.divergence = DivergenceDetector(df=df)
        
        for imp in impulses:
            points = imp['points']
            if len(points) < 6:
                continue
            
            p0 = points[0][1]
            p5 = points[5][1]
            
            # Проверка дивергенции W3/W5
            div = self.divergence.check_w3_w5_divergence(imp)
            
            if not div.get('divergence'):
                continue
            
            # Размер импульса
            impulse_size = abs(p5 - p0)
            if impulse_size == 0:
                continue
            
            # Направление: ПРОТИВ импульса (разворот)
            if imp['direction'] == 'bullish':
                direction = 'SELL'
                target_price = p5 - impulse_size * self.min_retracement
                stop_price = p5 + impulse_size * 0.1
            else:
                direction = 'BUY'
                target_price = p5 + impulse_size * self.min_retracement
                stop_price = p5 - impulse_size * 0.1
            
            trades.append({
                'entry_time': points[5][0],
                'entry_price': p5,
                'direction': direction,
                'target': target_price,
                'stop': stop_price,
                'pattern': 'W5_divergence',
                'divergence_type': div.get('type'),
                'source': imp,
            })
        
        return trades
