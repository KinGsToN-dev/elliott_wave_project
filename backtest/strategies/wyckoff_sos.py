"""Wyckoff SOS Strategy — покупка после SOS в Accumulation."""
from .wyckoff_base import WyckoffBaseStrategy
from wyckoff.phases import Phase


class WyckoffSOSStrategy(WyckoffBaseStrategy):
    """SOS + LPS в Accumulation → BUY."""
    
    def __init__(
        self,
        target_atr_mult: float = 3.0,
        stop_atr_mult: float = 0.7,
        min_confidence: float = 0.5,
    ):
        super().__init__(
            name="Wyckoff SOS",
            target_atr_mult=target_atr_mult,
            stop_atr_mult=stop_atr_mult,
            min_confidence=min_confidence,
        )
        self.description = "Sign of Strength в Accumulation"
    
    def should_enter(self, analysis, idx, df):
        """Проверяет SOS + Accumulation/Markup."""
        if analysis is None:
            return None
        
        if analysis.current_phase is None:
            return None
        
        # SOS работает после Accumulation или в начале Markup
        phase = analysis.current_phase.phase
        if phase not in (Phase.ACCUMULATION, Phase.MARKUP):
            return None
        if analysis.current_phase.confidence < self.min_confidence:
            return None
        
        # Ищем SOS
        sos = self._find_event_by_type(analysis, 'SOS')
        if sos is None:
            return None
        
        if abs(idx - sos.idx) > 5:
            return None
        
        # Проверяем, есть ли LPS (подтверждение)
        lps = self._find_event_by_type(analysis, 'LPS')
        confidence_bonus = 0.1 if lps else 0.0
        
        return {
            'direction': 'BUY',
            'pattern': 'SOS' + ('+LPS' if lps else ''),
            'confidence': min(
                1.0,
                analysis.current_phase.confidence + confidence_bonus
            ),
            'entry_price': float(df.iloc[idx]['close']),
        }