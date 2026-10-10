"""
CombinedStrategy - Комбинированная стратегия.

Логика:
- Запускает несколько стратегий.
- Собирает все сигналы вместе.
- Позволяет получить максимум сделок.
"""
from .base import BaseStrategy
from .w2_w3 import W2W3Strategy
from .w4_w5 import W4W5Strategy
from .wc_reversal import WCReversalStrategy


class CombinedStrategy(BaseStrategy):
    """Комбинированная стратегия (все сигналы)."""
    
    def __init__(self):
        super().__init__(name="Combined (All)")
        self.description = "Все стратегии вместе"
        self.strategies = [
            W2W3Strategy(),
            W4W5Strategy(),
            WCReversalStrategy(),
        ]
    
    def generate_signals(self, df, impulses=None, diagonals=None, corrections=None, combinations=None):
        all_signals = []
        
        for strategy in self.strategies:
            try:
                signals = strategy.generate_signals(df, impulses, diagonals, corrections, combinations)
                for sig in signals:
                    sig['combined_source'] = strategy.name
                all_signals.extend(signals)
            except Exception:
                continue
        
        # Сортируем по времени
        all_signals.sort(key=lambda x: x['entry_time'])
        
        return all_signals
