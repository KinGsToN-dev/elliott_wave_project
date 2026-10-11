"""Wyckoff SOS Strategy — покупка после SOS."""
from .wyckoff_base import WyckoffBaseStrategy
from wyckoff.phases import Phase


class WyckoffSOSStrategy(WyckoffBaseStrategy):
    """SOS в Accumulation/Markup → BUY."""
    
    def __init__(
        self,
        target_atr_mult: float = 3.0,
        stop_atr_mult: float = 0.7,
        min_confidence: float = 0.3,
    ):
        super().__init__(
            name="Wyckoff SOS",
            target_atr_mult=target_atr_mult,
            stop_atr_mult=stop_atr_mult,
            min_confidence=min_confidence,
        )
        self.description = "Sign of Strength"
    
    def _check_event(self, analysis, event, df):
        if event.type != 'SOS':
            return None
        
        if analysis.current_phase is not None:
            phase = analysis.current_phase.phase
            if phase not in (Phase.ACCUMULATION, Phase.MARKUP):
                return None
        
        has_lps = any(e.type == 'LPS' for e in analysis.events)
        idx = min(event.idx + 1, len(df) - 1)
        return {
            'direction': 'BUY',
            'pattern': 'SOS' + ('+LPS' if has_lps else ''),
            'confidence': event.confidence,
            'entry_price': float(df.iloc[idx]['close']),
        }