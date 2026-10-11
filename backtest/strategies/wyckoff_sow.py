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
        """SOW + вход на LPSY после SOW (по книге стр. 176-177)."""
        if event.type != 'SOW':
            return None
        
        # ТФ-проверка: SOW на D1+ не торгуем
        import pandas as pd
        try:
            idx_series = pd.Series(df.index)
            median_delta = idx_series.diff().median()
            hours = median_delta.total_seconds() / 3600
        except Exception:
            hours = 4
        
        if hours >= 20:
            return None
        
        if analysis.current_phase is not None:
            phase = analysis.current_phase.phase
            if phase == Phase.ACCUMULATION:
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
        
        lpsy = None
        for e in analysis.events:
            if (e.type == 'LPSY' and 
                event.idx < e.idx <= event.idx + window):
                lpsy = e
                break
        
        if lpsy is None:
            return None
        
        idx = min(lpsy.idx + 1, len(df) - 1)
        return {
            'direction': 'SELL',
            'pattern': 'SOW+LPSY',
            'confidence': event.confidence,
            'entry_price': float(df.iloc[idx]['close']),
        }