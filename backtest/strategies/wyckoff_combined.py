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
        """
        Combined — только СИЛЬНЫЕ сигналы (по книге).
        
        Spring (с Test), SOS (с LPS), SOW (с LPSY), UT (с Test).
        НЕ: SC, AR, ST, PS — это части структуры, не сигналы.
        """
        # === BULLISH ===
        if event.type == 'Spring':
            spring_type = event.meta.get('spring_type', 1)
            
            if spring_type == 3:
                idx = min(event.idx + 1, len(df) - 1)
                return {
                    'direction': 'BUY',
                    'pattern': 'Spring#3',
                    'confidence': event.confidence,
                    'entry_price': float(df.iloc[idx]['close']),
                }
            
            test = None
            for e in analysis.events:
                if (e.type == 'Test' and 
                    event.idx < e.idx <= event.idx + 30):
                    test = e
                    break
            
            if test is None:
                return None
            
            idx = min(test.idx + 1, len(df) - 1)
            return {
                'direction': 'BUY',
                'pattern': f'Spring#{spring_type}+Test',
                'confidence': event.confidence,
                'entry_price': float(df.iloc[idx]['close']),
            }
        
        if event.type == 'SOS':
            lps = None
            for e in analysis.events:
                if (e.type == 'LPS' and 
                    event.idx < e.idx <= event.idx + 30):
                    lps = e
                    break
            
            if lps is None:
                return None
            
            idx = min(lps.idx + 1, len(df) - 1)
            return {
                'direction': 'BUY',
                'pattern': 'SOS+LPS',
                'confidence': event.confidence,
                'entry_price': float(df.iloc[idx]['close']),
            }
        
        # === BEARISH ===
        if event.type in ('UT', 'UTAD'):
            test = None
            for e in analysis.events:
                if (e.type == 'Test' and 
                    event.idx < e.idx <= event.idx + 30):
                    test = e
                    break
            
            if test is None:
                return None
            
            idx = min(test.idx + 1, len(df) - 1)
            return {
                'direction': 'SELL',
                'pattern': f'{event.type}+Test',
                'confidence': event.confidence,
                'entry_price': float(df.iloc[idx]['close']),
            }
        
        if event.type == 'SOW':
            lpsy = None
            for e in analysis.events:
                if (e.type == 'LPSY' and 
                    event.idx < e.idx <= event.idx + 30):
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
        
        return None