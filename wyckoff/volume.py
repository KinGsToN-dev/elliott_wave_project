"""
Wyckoff Volume Analysis (VSA) - анализ объёма.

Основано на:
- Книга Хатсона "Метод Вайкоффа" (части 5-7)
- Том Вильямс, "Master the Markets" (VSA)

Ключевые концепции:
1. Effort vs Result - усилие (объём) vs результат (цена)
2. Stopping Volume  - объём остановки
3. Climactic Volume - кульминационный объём
4. Wide/Narrow Spread - широкий/узкий спред
5. Volume at S/R    - объём на уровнях
6. Volume Trend     - тренд объёма
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Dict

from wyckoff.ranges import TradingRange


@dataclass
class VolumeSignal:
    """Сигнал по объёму."""
    type: str           # 'effort_divergence', 'stopping_volume', 'climax', ...
    idx: int
    price: float
    volume: int
    direction: str      # 'bullish' / 'bearish' / 'neutral'
    strength: float     # 0..1
    meta: Dict = field(default_factory=dict)
    
    def __repr__(self):
        return (
            f"VolumeSignal({self.type} @ idx={self.idx}, "
            f"vol={self.volume}, dir={self.direction}, "
            f"str={self.strength:.2f})"
        )


class VolumeAnalyzer:
    """
    Анализ объёма по методу Вайкоффа / VSA.
    """
    
    def __init__(
        self,
        volume_ma_period: int = 20,
        spread_ma_period: int = 20,
        high_volume_mult: float = 1.5,
        low_volume_mult: float = 0.7,
        climactic_volume_mult: float = 2.5,
    ):
        """
        Параметры:
        ----------
        volume_ma_period : int
            Период MA объёма.
        spread_ma_period : int
            Период MA спреда (high-low).
        high_volume_mult : float
            Порог "высокого" объёма (× MA).
        low_volume_mult : float
            Порог "низкого" объёма (× MA).
        climactic_volume_mult : float
            Порог "кульминационного" объёма (× MA).
        """
        self.volume_ma_period = volume_ma_period
        self.spread_ma_period = spread_ma_period
        self.high_volume_mult = high_volume_mult
        self.low_volume_mult = low_volume_mult
        self.climactic_volume_mult = climactic_volume_mult
    
    # ============================================================
    # Базовые метрики
    # ============================================================
    def _compute_spread(self, df: pd.DataFrame) -> pd.Series:
        """Спред = high - low."""
        return df['high'] - df['low']
    
    def _compute_volume_ma(self, df: pd.DataFrame) -> pd.Series:
        """MA объёма."""
        if 'tick_volume' not in df.columns:
            return pd.Series([0] * len(df), index=df.index)
        return df['tick_volume'].rolling(
            window=self.volume_ma_period, min_periods=1
        ).mean()
    
    def _compute_spread_ma(self, df: pd.DataFrame) -> pd.Series:
        """MA спреда."""
        spread = self._compute_spread(df)
        return spread.rolling(
            window=self.spread_ma_period, min_periods=1
        ).mean()
    
    def _compute_volume_ratio(
        self,
        df: pd.DataFrame,
    ) -> pd.Series:
        """Отношение объёма к MA."""
        vol_ma = self._compute_volume_ma(df)
        if 'tick_volume' not in df.columns:
            return pd.Series([1.0] * len(df), index=df.index)
        ratio = df['tick_volume'] / vol_ma
        return ratio.fillna(1.0)
    
    def _compute_spread_ratio(
        self,
        df: pd.DataFrame,
    ) -> pd.Series:
        """Отношение спреда к MA."""
        spread = self._compute_spread(df)
        spread_ma = self._compute_spread_ma(df)
        ratio = spread / spread_ma
        return ratio.fillna(1.0)
    
    # ============================================================
    # 1. Effort vs Result
    # ============================================================
    def find_effort_divergence(
        self,
        df: pd.DataFrame,
    ) -> List[VolumeSignal]:
        """
        Effort vs Result - расхождение между усилием и результатом.
        
        Бычье расхождение:
        - Большой объём (усилие)
        - Цена закрылась в верхней части бара (результат слабый вниз)
        - Цена падала, но не смогла упасть дальше
        
        Медвежье расхождение:
        - Большой объём
        - Цена закрылась в нижней части бара
        - Цена росла, но не смогла вырасти дальше
        """
        signals = []
        vol_ratio = self._compute_volume_ratio(df)
        
        for i in range(1, len(df) - 1):
            row = df.iloc[i]
            vr = vol_ratio.iloc[i]
            
            if vr < self.high_volume_mult:
                continue
            
            high = row['high']
            low = row['low']
            close = row['close']
            spread = high - low
            
            if spread <= 0:
                continue
            
            # Позиция закрытия в баре (0 = низ, 1 = верх)
            close_pos = (close - low) / spread
            
            # Бычье: высокий объём + закрытие в верхней половине
            # на фоне падения (предыдущий бар ниже)
            if close_pos >= 0.7 and i > 0:
                prev_close = df.iloc[i - 1]['close']
                if close < prev_close:
                    signals.append(VolumeSignal(
                        type='effort_divergence',
                        idx=i,
                        price=float(close),
                        volume=int(row['tick_volume']),
                        direction='bullish',
                        strength=min(1.0, (vr - 1.0) / 2.0),
                        meta={'vol_ratio': round(vr, 2), 'close_pos': round(close_pos, 2)},
                    ))
            
            # Медвежье: высокий объём + закрытие в нижней половине
            # на фоне роста
            if close_pos <= 0.3 and i > 0:
                prev_close = df.iloc[i - 1]['close']
                if close > prev_close:
                    signals.append(VolumeSignal(
                        type='effort_divergence',
                        idx=i,
                        price=float(close),
                        volume=int(row['tick_volume']),
                        direction='bearish',
                        strength=min(1.0, (vr - 1.0) / 2.0),
                        meta={'vol_ratio': round(vr, 2), 'close_pos': round(close_pos, 2)},
                    ))
        
        return signals
    
    # ============================================================
    # 2. Stopping Volume
    # ============================================================
    def find_stopping_volume(
        self,
        df: pd.DataFrame,
    ) -> List[VolumeSignal]:
        """
        Stopping Volume - объём остановки падения.
        
        Признаки:
        - Большой объём
        - Резкое падение (low < prev_low)
        - Закрытие выше минимума (отскок)
        - Следующий бар подтверждает (не пробивает low)
        """
        signals = []
        vol_ratio = self._compute_volume_ratio(df)
        
        for i in range(1, len(df) - 1):
            row = df.iloc[i]
            next_row = df.iloc[i + 1]
            prev_row = df.iloc[i - 1]
            vr = vol_ratio.iloc[i]
            
            if vr < self.high_volume_mult:
                continue
            
            # Продолжение падения
            if row['low'] < prev_row['low']:
                # Закрытие выше минимума
                spread = row['high'] - row['low']
                if spread <= 0:
                    continue
                close_pos = (row['close'] - row['low']) / spread
                
                # Закрытие в верхней половине
                if close_pos >= 0.5:
                    # Следующий бар не пробивает low
                    if next_row['low'] >= row['low']:
                        signals.append(VolumeSignal(
                            type='stopping_volume',
                            idx=i,
                            price=float(row['low']),
                            volume=int(row['tick_volume']),
                            direction='bullish',
                            strength=min(1.0, (vr - 1.0) / 2.0),
                            meta={
                                'vol_ratio': round(vr, 2),
                                'close_pos': round(close_pos, 2),
                            },
                        ))
        
        return signals
    
    # ============================================================
    # 3. Climactic Volume
    # ============================================================
    def find_climactic_volume(
        self,
        df: pd.DataFrame,
    ) -> List[VolumeSignal]:
        """
        Climactic Volume - кульминационный объём.
        
        Selling Climax:
        - Очень большой объём (climactic_volume_mult × MA)
        - Широкий спред
        - Цена в нижней части
        - Закрытие в верхней части (отскок)
        
        Buying Climax:
        - Очень большой объём
        - Широкий спред
        - Цена в верхней части
        - Закрытие в нижней части (откат)
        """
        signals = []
        vol_ratio = self._compute_volume_ratio(df)
        spread_ratio = self._compute_spread_ratio(df)
        
        for i in range(1, len(df)):
            row = df.iloc[i]
            vr = vol_ratio.iloc[i]
            sr = spread_ratio.iloc[i]
            
            if vr < self.climactic_volume_mult:
                continue
            
            spread = row['high'] - row['low']
            if spread <= 0:
                continue
            
            close_pos = (row['close'] - row['low']) / spread
            
            # Selling Climax: широкий спред, закрытие в верхней части
            if sr >= 1.5 and close_pos >= 0.6:
                signals.append(VolumeSignal(
                    type='selling_climax',
                    idx=i,
                    price=float(row['low']),
                    volume=int(row['tick_volume']),
                    direction='bullish',
                    strength=min(1.0, (vr - 1.0) / 3.0),
                    meta={
                        'vol_ratio': round(vr, 2),
                        'spread_ratio': round(sr, 2),
                        'close_pos': round(close_pos, 2),
                    },
                ))
            
            # Buying Climax: широкий спред, закрытие в нижней части
            if sr >= 1.5 and close_pos <= 0.4:
                signals.append(VolumeSignal(
                    type='buying_climax',
                    idx=i,
                    price=float(row['high']),
                    volume=int(row['tick_volume']),
                    direction='bearish',
                    strength=min(1.0, (vr - 1.0) / 3.0),
                    meta={
                        'vol_ratio': round(vr, 2),
                        'spread_ratio': round(sr, 2),
                        'close_pos': round(close_pos, 2),
                    },
                ))
        
        return signals
    
    # ============================================================
    # 4. Volume at Support/Resistance
    # ============================================================
    def analyze_volume_at_range(
        self,
        df: pd.DataFrame,
        r: TradingRange,
    ) -> Dict[str, float]:
        """
        Анализ объёма на границах range.
        
        Возвращает:
        - vol_at_support: средний объём при касании нижней границы
        - vol_at_resistance: средний объём при касании верхней границы
        - vol_ratio: vol_at_resistance / vol_at_support
        - interpretation: текстовая интерпретация
        """
        atr = self._compute_spread(df).iloc[r.start_idx:r.end_idx + 1].mean()
        tolerance = 0.3 * atr if atr > 0 else 0.001
        
        support_volumes = []
        resistance_volumes = []
        
        for i in range(r.start_idx, min(r.end_idx + 1, len(df))):
            row = df.iloc[i]
            vol = row['tick_volume'] if 'tick_volume' in df.columns else 0
            
            # Касание поддержки
            if row['low'] <= r.lower + tolerance:
                support_volumes.append(vol)
            
            # Касание сопротивления
            if row['high'] >= r.upper - tolerance:
                resistance_volumes.append(vol)
        
        avg_support = np.mean(support_volumes) if support_volumes else 0
        avg_resistance = np.mean(resistance_volumes) if resistance_volumes else 0
        
        vol_ratio = (avg_resistance / avg_support) if avg_support > 0 else 1.0
        
        if vol_ratio > 1.3:
            interp = 'объём выше у сопротивления → давление продаж'
        elif vol_ratio < 0.77:
            interp = 'объём выше у поддержки → давление покупок'
        else:
            interp = 'объём сбалансирован'
        
        return {
            'vol_at_support': float(avg_support),
            'vol_at_resistance': float(avg_resistance),
            'vol_ratio': round(vol_ratio, 2),
            'touches_support': len(support_volumes),
            'touches_resistance': len(resistance_volumes),
            'interpretation': interp,
        }
    
    # ============================================================
    # 5. Wide/Narrow Spread
    # ============================================================
    def analyze_spread(
        self,
        df: pd.DataFrame,
        window: int = 50,
    ) -> Dict[str, float]:
        """
        Анализ спреда (ширины бара).
        
        Narrow spread + low volume  = консолидация
        Wide spread + high volume   = тренд
        Narrow spread + high volume = борьба (скрытая активность)
        """
        if len(df) < window:
            window = len(df)
        
        recent = df.iloc[-window:]
        spread_ratio = self._compute_spread_ratio(df).iloc[-window:]
        vol_ratio = self._compute_volume_ratio(df).iloc[-window:]
        
        avg_spread_ratio = spread_ratio.mean()
        avg_vol_ratio = vol_ratio.mean()
        
        if avg_spread_ratio < 0.8 and avg_vol_ratio < 0.8:
            regime = 'consolidation'
            interp = 'узкий спред + низкий объём → консолидация'
        elif avg_spread_ratio > 1.2 and avg_vol_ratio > 1.2:
            regime = 'trend'
            interp = 'широкий спред + высокий объём → тренд'
        elif avg_spread_ratio < 0.8 and avg_vol_ratio > 1.2:
            regime = 'struggle'
            interp = 'узкий спред + высокий объём → скрытая борьба'
        else:
            regime = 'neutral'
            interp = 'нейтральный режим'
        
        return {
            'avg_spread_ratio': round(avg_spread_ratio, 2),
            'avg_vol_ratio': round(avg_vol_ratio, 2),
            'regime': regime,
            'interpretation': interp,
        }
    
    # ============================================================
    # 6. Volume Trend
    # ============================================================
    def find_volume_trend(
        self,
        df: pd.DataFrame,
        window: int = 20,
    ) -> str:
        """
        Определяет тренд объёма:
        - 'increasing' — объём растёт
        - 'decreasing' — объём падает
        - 'flat'       — стабильный
        """
        if len(df) < window:
            window = len(df)
        
        vol_ma = self._compute_volume_ma(df).iloc[-window:]
        
        if len(vol_ma) < 2:
            return 'flat'
        
        first = vol_ma.iloc[:len(vol_ma) // 2].mean()
        second = vol_ma.iloc[len(vol_ma) // 2:].mean()
        
        if first <= 0:
            return 'flat'
        
        change = (second - first) / first
        
        if change > 0.2:
            return 'increasing'
        elif change < -0.2:
            return 'decreasing'
        return 'flat'
    
    # ============================================================
    # Полный анализ
    # ============================================================
    def analyze(
        self,
        df: pd.DataFrame,
        r: Optional[TradingRange] = None,
    ) -> Dict:
        """
        Полный анализ объёма.
        """
        result = {
            'signals': [],
            'volume_trend': self.find_volume_trend(df),
            'spread_analysis': self.analyze_spread(df),
        }
        
        # Все сигналы
        result['signals'].extend(self.find_effort_divergence(df))
        result['signals'].extend(self.find_stopping_volume(df))
        result['signals'].extend(self.find_climactic_volume(df))
        
        # Анализ на границах range
        if r is not None:
            result['range_analysis'] = self.analyze_volume_at_range(df, r)
        
        return result