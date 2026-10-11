"""Wyckoff SOW Strategy — продажа после SOW."""
from .wyckoff_base import WyckoffBaseStrategy
from wyckoff.phases import Phase


class WyckoffSOWStrategy(WyckoffBaseStrategy):
    """SOW в Distribution/Markdown → SELL."""
    
    def __init__(
        self,
        target_atr_mult: float = 3.0,
        stop_atr_mult: float = 0.7,
        min_confidence: float = 0.3,
        ema_period: int = 200,
    ):
        super().__init__(
            name="Wyckoff SOW",
            target_atr_mult=target_atr_mult,
            stop_atr_mult=stop_atr_mult,
            min_confidence=min_confidence,
            ema_period=ema_period,
        )
        self.description = "Sign of Weakness"
    
    def _check_event(self, analysis, event, df):
        if event.type != 'SOW':
            return None
        
        if analysis.current_phase is not None:
            phase = analysis.current_phase.phase
            # Разрешаем SOW в Distribution, Markdown, но НЕ в Accumulation
            if phase == Phase.ACCUMULATION:
                return None
        
        has_lpsy = any(e.type == 'LPSY' for e in analysis.events)
        idx = min(event.idx + 1, len(df) - 1)
        return {
            'direction': 'SELL',
            'pattern': 'SOW' + ('+LPSY' if has_lpsy else ''),
            'confidence': event.confidence,
            'entry_price': float(df.iloc[idx]['close']),
        }