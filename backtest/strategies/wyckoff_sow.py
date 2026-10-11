"""Wyckoff SOW Strategy — продажа после SOW в Distribution."""
from .wyckoff_base import WyckoffBaseStrategy
from wyckoff.phases import Phase


class WyckoffSOWStrategy(WyckoffBaseStrategy):
    """SOW + LPSY в Distribution → SELL."""
    
    def __init__(
        self,
        target_atr_mult: float = 3.0,
        stop_atr_mult: float = 0.7,
        min_confidence: float = 0.5,
    ):
        super().__init__(
            name="Wyckoff SOW",
            target_atr_mult=target_atr_mult,
            stop_atr_mult=stop_atr_mult,
            min_confidence=min_confidence,
        )
        self.description = "Sign of Weakness в Distribution"
    
    def should_enter(self, analysis, idx, df):
        """Проверяет SOW + Distribution/Markdown."""
        if analysis is None:
            return None
        
        if analysis.current_phase is None:
            return None
        
        phase = analysis.current_phase.phase
        if phase not in (Phase.DISTRIBUTION, Phase.MARKDOWN):
            return None
        if analysis.current_phase.confidence < self.min_confidence:
            return None
        
        # Ищем SOW
        sow = self._find_event_by_type(analysis, 'SOW')
        if sow is None:
            return None
        
        if abs(idx - sow.idx) > 5:
            return None
        
        lpsy = self._find_event_by_type(analysis, 'LPSY')
        confidence_bonus = 0.1 if lpsy else 0.0
        
        return {
            'direction': 'SELL',
            'pattern': 'SOW' + ('+LPSY' if lpsy else ''),
            'confidence': min(
                1.0,
                analysis.current_phase.confidence + confidence_bonus
            ),
            'entry_price': float(df.iloc[idx]['close']),
        }