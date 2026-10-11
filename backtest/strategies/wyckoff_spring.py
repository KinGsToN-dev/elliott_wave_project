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
        ema_period: int = 200,
    ):
        super().__init__(
            name="Wyckoff Spring",
            target_atr_mult=target_atr_mult,
            stop_atr_mult=stop_atr_mult,
            min_confidence=min_confidence,
            ema_period=ema_period,
        )
        self.description = "Spring в Accumulation"
    
    def _check_event(self, analysis, event, df):
        """Spring с учётом типа."""
        if event.type != 'Spring':
            return None
        
        spring_type = event.meta.get('spring_type', 1)
        
        # Проверка фазы
        if analysis.current_phase is not None:
            phase = analysis.current_phase.phase
            if phase not in (Phase.ACCUMULATION, Phase.MARKUP):
                return None
        
        # Spring #3 (истощение) — входить сразу
        if spring_type == 3:
            idx = min(event.idx + 1, len(df) - 1)
            return {
                'direction': 'BUY',
                'pattern': 'Spring#3',
                'confidence': event.confidence,
                'entry_price': float(df.iloc[idx]['close']),
            }
        
        # Spring #1, #2 — ждать Test ПОСЛЕ ЭТОГО Spring
        test = None
        for e in analysis.events:
            if (e.type == 'Test' and 
                event.idx < e.idx <= event.idx + 30):
                test = e
                break
        
        if test is None:
            return None
        
        # Вход на Test
        idx = min(test.idx + 1, len(df) - 1)
        return {
            'direction': 'BUY',
            'pattern': f'Spring#{spring_type}+Test',
            'confidence': event.confidence,
            'entry_price': float(df.iloc[idx]['close']),
        }