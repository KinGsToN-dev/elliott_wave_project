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
        ema_period: int = 200,
    ):
        super().__init__(
            name="Wyckoff SOS",
            target_atr_mult=target_atr_mult,
            stop_atr_mult=stop_atr_mult,
            min_confidence=min_confidence,
            ema_period=ema_period,
        )
        self.description = "Sign of Strength"
    
    def _check_event(self, analysis, event, df):
        """SOS + вход на LPS после SOS (по книге стр. 173-175)."""
        if event.type != 'SOS':
            return None
        
        if analysis.current_phase is not None:
            phase = analysis.current_phase.phase
            if phase not in (Phase.ACCUMULATION, Phase.MARKUP):
                return None
        
        # Ищем LPS ПОСЛЕ ЭТОГО SOS (в пределах 30 баров)
        lps = None
        for e in analysis.events:
            if (e.type == 'LPS' and 
                event.idx < e.idx <= event.idx + 30):
                lps = e
                break
        
        # Вход НЕ на SOS, а на LPS
        if lps is None:
            return None
        
        idx = min(lps.idx + 1, len(df) - 1)
        return {
            'direction': 'BUY',
            'pattern': 'SOS+LPS',
            'confidence': event.confidence,
            'entry_price': float(df.iloc[idx]['close']),
        }