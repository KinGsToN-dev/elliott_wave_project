"""Wyckoff Combined Strategy — все сигналы вместе."""
from .wyckoff_base import WyckoffBaseStrategy
from wyckoff.phases import Phase


class WyckoffCombinedStrategy(WyckoffBaseStrategy):
    """Комбинированная — все Wyckoff сигналы."""
    
    def __init__(
        self,
        target_atr_mult: float = 2.5,
        stop_atr_mult: float = 0.7,
        min_confidence: float = 0.4,
        ema_period: int = 200,
    ):
        super().__init__(
            name="Wyckoff Combined",
            target_atr_mult=target_atr_mult,
            stop_atr_mult=stop_atr_mult,
            min_confidence=min_confidence,
            ema_period=ema_period,
        )
        self.description = "Все Wyckoff сигналы"
    
    def should_enter(self, analysis, idx, df):
        """Ищет любой Wyckoff сигнал."""
        if analysis is None:
            return None
        
        if analysis.current_phase is None:
            return None
        if analysis.current_phase.confidence < self.min_confidence:
            return None
        
        phase = analysis.current_phase.phase
        
        # Spring + Accumulation
        if phase == Phase.ACCUMULATION:
            spring = self._find_event_by_type(analysis, 'Spring')
            if spring and abs(idx - spring.idx) <= 5:
                return {
                    'direction': 'BUY',
                    'pattern': 'Spring',
                    'confidence': analysis.current_phase.confidence,
                    'entry_price': float(df.iloc[idx]['close']),
                }
            sos = self._find_event_by_type(analysis, 'SOS')
            if sos and abs(idx - sos.idx) <= 5:
                return {
                    'direction': 'BUY',
                    'pattern': 'SOS',
                    'confidence': analysis.current_phase.confidence,
                    'entry_price': float(df.iloc[idx]['close']),
                }
        
        # UT + Distribution
        if phase == Phase.DISTRIBUTION:
            ut = self._find_event_by_type(analysis, 'UT')
            if ut and abs(idx - ut.idx) <= 5:
                return {
                    'direction': 'SELL',
                    'pattern': 'UT',
                    'confidence': analysis.current_phase.confidence,
                    'entry_price': float(df.iloc[idx]['close']),
                }
            sow = self._find_event_by_type(analysis, 'SOW')
            if sow and abs(idx - sow.idx) <= 5:
                return {
                    'direction': 'SELL',
                    'pattern': 'SOW',
                    'confidence': analysis.current_phase.confidence,
                    'entry_price': float(df.iloc[idx]['close']),
                }
        
        return None

    def _check_event(self, analysis, event, df):
        """Любой Wyckoff signal."""
        bullish = {'SC', 'AR', 'ST', 'SOS', 'LPS', 'Spring', 'Test'}
        bearish = {'UT', 'SOW', 'LPSY'}
        
        if event.type in bullish:
            direction = 'BUY'
        elif event.type in bearish:
            direction = 'SELL'
        else:
            return None
        
        idx = min(event.idx + 1, len(df) - 1)
        return {
            'direction': direction,
            'pattern': event.type,
            'confidence': event.confidence,
            'entry_price': float(df.iloc[idx]['close']),
        }