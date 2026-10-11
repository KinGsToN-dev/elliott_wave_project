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
        higher_tf_phase: str = None,
    ):
        super().__init__(
            name="Wyckoff SOS",
            target_atr_mult=target_atr_mult,
            stop_atr_mult=stop_atr_mult,
            min_confidence=min_confidence,
            ema_period=ema_period,
            higher_tf_phase=higher_tf_phase,
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
        
        import pandas as pd
        try:
            idx_series = pd.Series(df.index)
            median_delta = idx_series.diff().median()
            hours = median_delta.total_seconds() / 3600
            if hours >= 100:
                window = 90
            elif hours >= 20:
                window = 60
            else:
                window = 30
        except Exception:
            window = 30
        
        lps = None
        for e in analysis.events:
            if (e.type == 'LPS' and 
                event.idx < e.idx <= event.idx + window):
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