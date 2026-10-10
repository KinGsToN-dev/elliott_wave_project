"""
MTFConfirmedStrategy - Стратегия с MTF-подтверждением.

Логика:
- Берём сигналы от W2→W3.
- Фильтруем по тренду на текущем ТФ (EMA 200).
- Вход: только по направлению тренда.
"""
from .base import BaseStrategy
from .w2_w3 import W2W3Strategy


class MTFConfirmedStrategy(BaseStrategy):
    """Стратегия W2→W3 с MTF-подтверждением."""
    
    def __init__(self, ema_len=200):
        super().__init__(name="W2→W3 + MTF")
        self.description = "W2→W3 с фильтром по EMA на текущем ТФ"
        self.ema_len = ema_len
        self.base = W2W3Strategy()
    
    def generate_signals(self, df, impulses=None, diagonals=None, corrections=None, combinations=None):
        # Получаем базовые сигналы
        base_signals = self.base.generate_signals(df, impulses, diagonals, corrections, combinations)
        
        if not base_signals:
            return []
        
        # Считаем EMA
        ema_len = min(self.ema_len, len(df) - 1)
        ema = df['close'].ewm(span=ema_len, adjust=False).mean()
        
        filtered = []
        for sig in base_signals:
            entry_time = sig['entry_time']
            
            # Проверяем, что entry_time есть в индексе
            try:
                if entry_time not in ema.index:
                    continue
                ema_value = ema.loc[entry_time]
                entry_price = sig['entry_price']
            except Exception:
                continue
            
            # Фильтр по тренду
            if sig['direction'] == 'BUY' and entry_price > ema_value:
                filtered.append(sig)
            elif sig['direction'] == 'SELL' and entry_price < ema_value:
                filtered.append(sig)
        
        return filtered
