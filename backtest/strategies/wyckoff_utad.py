"""Wyckoff UTAD Strategy — продажа после UT в Distribution."""
from .wyckoff_base import WyckoffBaseStrategy
from wyckoff.phases import Phase


class WyckoffUTADStrategy(WyckoffBaseStrategy):
    """UT в Distribution → SELL."""
    
    def __init__(
        self,
        target_atr_mult: float = 2.5,
        stop_atr_mult: float = 0.5,
        min_confidence: float = 0.5,
    ):
        super().__init__(
            name="Wyckoff UT",
            target_atr_mult=target_atr_mult,
            stop_atr_mult=stop_atr_mult,
            min_confidence=min_confidence,
        )
        self.description = "Upthrust в Distribution"
    
    def should_enter(self, analysis, idx, df):
        """Проверяет UT + Distribution."""
        if analysis is None:
            return None
        
        if analysis.current_phase is None:
            return None
        if analysis.current_phase.phase != Phase.DISTRIBUTION:
            return None
        if analysis.current_phase.confidence < self.min_confidence:
            return None
        
        # Ищем UT
        ut = self._find_event_by_type(analysis, 'UT')
        if ut is None:
            return None
        
        if abs(idx - ut.idx) > 5:
            return None
        
        return {
            'direction': 'SELL',
            'pattern': 'UT',
            'confidence': analysis.current_phase.confidence,
            'entry_price': float(df.iloc[idx]['close']),
        }