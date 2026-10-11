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
        higher_tf_phase: str = None,
    ):
        super().__init__(
            name="Wyckoff Combined",
            target_atr_mult=target_atr_mult,
            stop_atr_mult=stop_atr_mult,
            min_confidence=min_confidence,
            ema_period=ema_period,
            higher_tf_phase=higher_tf_phase,
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
        """Combined — только СИЛЬНЫЕ сигналы (мягкая проверка фазы)."""
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
        
        # Мягкая проверка фазы
        phase = None
        if analysis.current_phase is not None:
            phase = analysis.current_phase.phase
        
        # === BULLISH ===
        if event.type == 'Spring':
            # Блокируем BUY только в Distribution/Markdown
            if phase == Phase.DISTRIBUTION or phase == Phase.MARKDOWN:
                return None
            
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
                    event.idx < e.idx <= event.idx + window):
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
            if phase == Phase.DISTRIBUTION or phase == Phase.MARKDOWN:
                return None
            
            lps = None
            for e in analysis.events:
                if (e.type == 'LPS' and 
                    event.idx < e.idx <= event.idx + window):
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
            if phase == Phase.ACCUMULATION or phase == Phase.MARKUP:
                return None
            
            test = None
            for e in analysis.events:
                if (e.type == 'Test' and 
                    event.idx < e.idx <= event.idx + window):
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
            if phase == Phase.ACCUMULATION or phase == Phase.MARKUP:
                return None
            
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
        
        return None