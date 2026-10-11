"""Wyckoff Spring Strategy — покупка после Spring в Accumulation."""
from .wyckoff_base import WyckoffBaseStrategy
from wyckoff.phases import Phase


class WyckoffSpringStrategy(WyckoffBaseStrategy):
    """Spring в Accumulation → BUY."""
    
    def __init__(
        self,
        target_atr_mult: float = 2.5,
        stop_atr_mult: float = 0.5,
        min_confidence: float = 0.5,
    ):
        super().__init__(
            name="Wyckoff Spring",
            target_atr_mult=target_atr_mult,
            stop_atr_mult=stop_atr_mult,
            min_confidence=min_confidence,
        )
        self.description = "Spring в Accumulation"
    
    def should_enter(self, analysis, idx, df):
        """Проверяет Spring + Accumulation."""
        if analysis is None:
            return None
        
        # Должна быть Accumulation
        if analysis.current_phase is None:
            return None
        if analysis.current_phase.phase != Phase.ACCUMULATION:
            return None
        if analysis.current_phase.confidence < self.min_confidence:
            return None
        
        # Ищем Spring
        spring = self._find_event_by_type(analysis, 'Spring')
        if spring is None:
            return None
        
        # Бар входа должен быть близко к Spring (в пределах 5 баров)
        # idx в df — относительно окна анализа
        if abs(idx - spring.idx) > 5:
            return None
        
        return {
            'direction': 'BUY',
            'pattern': 'Spring',
            'confidence': analysis.current_phase.confidence,
            'entry_price': float(df.iloc[idx]['close']),
        }