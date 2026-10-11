"""Wyckoff Spring Strategy — покупка после Spring в Accumulation."""
from .wyckoff_base import WyckoffBaseStrategy
from wyckoff.phases import Phase


class WyckoffSpringStrategy(WyckoffBaseStrategy):
    """Spring в Accumulation → BUY."""
    
    def __init__(
        self,
        target_atr_mult: float = 2.5,
        stop_atr_mult: float = 0.7,
        min_confidence: float = 0.3,
    ):
        super().__init__(
            name="Wyckoff Spring",
            target_atr_mult=target_atr_mult,
            stop_atr_mult=stop_atr_mult,
            min_confidence=min_confidence,
        )
        self.description = "Spring в Accumulation"
    
    def _check_event(self, analysis, event, df):
        if event.type != 'Spring':
            return None
        
        if analysis.current_phase is not None:
            phase = analysis.current_phase.phase
            if phase not in (Phase.ACCUMULATION, Phase.MARKUP):
                return None
        
        idx = min(event.idx + 1, len(df) - 1)
        return {
            'direction': 'BUY',
            'pattern': 'Spring',
            'confidence': event.confidence,
            'entry_price': float(df.iloc[idx]['close']),
        }