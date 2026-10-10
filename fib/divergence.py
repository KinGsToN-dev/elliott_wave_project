"""
Divergence - Дивергенция MACD/AO между волнами.

Правила (traderevolution.by):
- Самый большой пик MACD/AO = конец W3 (или растянутой W5).
- Между W3 и W5 — дивергенция.
- Между A и C зигзага — дивергенция.
- Между W и Y двойного зигзага — дивергенция.
"""
import pandas as pd
import numpy as np


class DivergenceDetector:
    """Проверка дивергенции MACD/AO."""
    
    def __init__(self, df=None):
        self.df = df
        self.macd = None
        self.ao = None
        self.results = []
        
        if df is not None:
            self.macd = self._calculate_macd()
            self.ao = self._calculate_ao()
    
    def _calculate_macd(self, fast=12, slow=26, signal=9):
        """Расчёт MACD."""
        if self.df is None:
            return None
        
        close = self.df['close']
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram,
        }
    
    def _calculate_ao(self, fast=5, slow=34):
        """
        Расчёт AO (Awesome Oscillator).
        AO = SMA(median_price, 5) - SMA(median_price, 34)
        median_price = (high + low) / 2
        """
        if self.df is None:
            return None
        
        median_price = (self.df['high'] + self.df['low']) / 2
        sma_fast = median_price.rolling(window=fast).mean()
        sma_slow = median_price.rolling(window=slow).mean()
        ao = sma_fast - sma_slow
        
        return ao
    
    def get_macd_value_at(self, time):
        """MACD histogram в указанное время."""
        if self.macd is None:
            return None
        try:
            t = pd.to_datetime(time)
            if t in self.macd['histogram'].index:
                return float(self.macd['histogram'].loc[t])
        except Exception:
            pass
        return None
    
    def get_ao_value_at(self, time):
        """AO в указанное время."""
        if self.ao is None:
            return None
        try:
            t = pd.to_datetime(time)
            if t in self.ao.index:
                val = self.ao.loc[t]
                return float(val) if not pd.isna(val) else None
        except Exception:
            pass
        return None
    
    def check_divergence(self, p1_time, p1_price, p2_time, p2_price, indicator='macd'):
        """
        Проверка дивергенции между двумя точками.
        
        Args:
            p1_time, p1_price: первая точка
            p2_time, p2_price: вторая точка
            indicator: 'macd' или 'ao'
        """
        if indicator == 'ao':
            v1 = self.get_ao_value_at(p1_time)
            v2 = self.get_ao_value_at(p2_time)
        else:
            v1 = self.get_macd_value_at(p1_time)
            v2 = self.get_macd_value_at(p2_time)
        
        if v1 is None or v2 is None:
            return {'divergence': False, 'type': 'no_data', 'indicator': indicator}
        
        price_higher = p2_price > p1_price
        indicator_lower = v2 < v1
        
        if price_higher and indicator_lower:
            return {
                'divergence': True, 'type': 'bearish', 'indicator': indicator,
                'v1': v1, 'v2': v2, 'price1': p1_price, 'price2': p2_price,
            }
        elif not price_higher and not indicator_lower:
            return {
                'divergence': True, 'type': 'bullish', 'indicator': indicator,
                'v1': v1, 'v2': v2, 'price1': p1_price, 'price2': p2_price,
            }
        
        return {'divergence': False, 'type': 'none', 'indicator': indicator}
    
    def find_macd_peak(self, start_time, end_time, indicator='macd'):
        """
        Находит самый большой пик MACD/AO в диапазоне.
        Согласно правилам, это конец W3.
        """
        if indicator == 'ao' and self.ao is None:
            return None
        if indicator == 'macd' and self.macd is None:
            return None
        
        series = self.ao if indicator == 'ao' else self.macd['histogram']
        
        try:
            t_start = pd.to_datetime(start_time)
            t_end = pd.to_datetime(end_time)
            subset = series.loc[t_start:t_end].abs()
            
            if len(subset) == 0:
                return None
            
            peak_time = subset.idxmax()
            peak_value = float(series.loc[peak_time])
            
            return {
                'peak_time': peak_time,
                'peak_value': peak_value,
                'indicator': indicator,
            }
        except Exception:
            return None
    
    def check_w3_w5_divergence(self, impulse, indicator='macd'):
        """Проверка W3/W5."""
        points = impulse['points']
        if len(points) < 6:
            return {'divergence': False, 'type': 'invalid'}
        
        w3_time, w3_price = points[3][0], points[3][1]
        w5_time, w5_price = points[5][0], points[5][1]
        
        result = self.check_divergence(w3_time, w3_price, w5_time, w5_price, indicator)
        result['rule'] = 'W3/W5'
        return result
    
    def check_ac_divergence(self, correction, indicator='macd'):
        """Проверка дивергенции A/C."""
        points = correction['points']
        if len(points) < 4:
            return {'divergence': False, 'type': 'invalid'}
        
        a_time, a_price = points[1][0], points[1][1]
        c_time, c_price = points[3][0], points[3][1]
        
        result = self.check_divergence(a_time, a_price, c_time, c_price, indicator)
        result['rule'] = 'A/C'
        return result
    
    def check_wy_divergence(self, combination, indicator='macd'):
        """Проверка дивергенции W/Y (двойная тройка)."""
        points = combination['points']
        if len(points) < 3:
            return {'divergence': False, 'type': 'invalid'}
        
        w_time, w_price = points[0][0], points[0][1]
        y_time, y_price = points[2][0], points[2][1]
        
        result = self.check_divergence(w_time, w_price, y_time, y_price, indicator)
        result['rule'] = 'W/Y'
        return result
    
    def calculate_all(self, impulses, corrections=None, combinations=None):
        """Расчёт дивергенций для всех паттернов."""
        self.results = []
        
        for imp in impulses:
            result = self.check_w3_w5_divergence(imp)
            self.results.append({
                'pattern_id': id(imp), 'type': 'impulse',
                'direction': imp['direction'], 'divergence': result,
            })
        
        if corrections:
            for corr in corrections:
                if corr['type'] in ['zigzag', 'flat']:
                    result = self.check_ac_divergence(corr)
                    self.results.append({
                        'pattern_id': id(corr), 'type': corr['type'],
                        'direction': corr['direction'], 'divergence': result,
                    })
        
        if combinations:
            for combo in combinations:
                if combo['type'] == 'double_three':
                    result = self.check_wy_divergence(combo)
                    self.results.append({
                        'pattern_id': id(combo), 'type': 'double_three',
                        'direction': combo['direction'], 'divergence': result,
                    })
        
        return self.results
    
    def get_results(self):
        return self.results
