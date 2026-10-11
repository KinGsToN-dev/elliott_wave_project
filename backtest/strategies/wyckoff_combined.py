"""Wyckoff Combined Strategy — все сигналы."""
from .wyckoff_base import WyckoffBaseStrategy
from wyckoff.phases import Phase


class WyckoffCombinedStrategy(WyckoffBaseStrategy):
    """Все Wyckoff сигналы."""
    
    def __init__(
        self,
        target_atr_mult: float = 2.5,
        stop_atr_mult: float = 0.7,
        min_confidence: float = 0.3,
    ):
        super().__init__(
            name="Wyckoff Combined",
            target_atr_mult=target_atr_mult,
            stop_atr_mult=stop_atr_mult,
            min_confidence=min_confidence,
        )
        self.description = "Все Wyckoff сигналы"
    
    def _check_event(self, analysis, event, df):
        """Любой Wyckoff signal."""
        bullish = {'SC', 'Spring', 'Test', 'SOS', 'LPS'}
        bearish = {'UT', 'UTAD', 'SOW', 'LPSY'}
        
        if event.type in bullish:
            direction = 'BUY'
        elif event.type in bearish:
            direction = 'SELL'
        else:
            return None
        
        idx = min(event.idx + 1, len(df) - 1)
        return {
            'direction': direction,
            'pattern': event.type,
            'confidence': event.confidence,
            'entry_price': float(df.iloc[idx]['close']),
        }