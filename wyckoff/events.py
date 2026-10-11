"""
Wyckoff Events - детекторы событий.

События взяты из книги Джека Хатсона "Метод Вайкоффа":
- PS   - Preliminary Support
- SC   - Selling Climax
- AR   - Automatic Rally
- ST   - Secondary Test
- Spring  - ложный пробой вниз
- Test    - повторный тест Spring
- SOS  - Sign of Strength
- LPS  - Last Point of Support
- UT   - Upthrust
- UTAD - Upthrust After Distribution
- SOW  - Sign of Weakness
- LPSY - Last Point of Supply

Все события возвращаются как WyckoffEvent с полями:
- type       : str  (PS, SC, AR, ST, Spring, ...)
- idx        : int  (индекс бара)
- price      : float (цена события)
- volume     : int  (объём)
- direction  : str  ('bullish' / 'bearish')
- confidence : float (0..1)
- meta       : dict (доп. поля)
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Dict

from wyckoff.ranges import TradingRange, TradingRangeDetector


@dataclass
class WyckoffEvent:
    """Одно событие Вайкоффа."""
    type: str
    idx: int
    price: float
    volume: int
    direction: str = 'bullish'  # 'bullish' или 'bearish'
    confidence: float = 1.0
    meta: Dict = field(default_factory=dict)
    
    def __repr__(self):
        return (
            f"WyckoffEvent({self.type} @ idx={self.idx}, "
            f"price={self.price:.5f}, vol={self.volume}, "
            f"dir={self.direction}, conf={self.confidence:.2f})"
        )


class WyckoffEventDetector:
    """
    Детектор событий Вайкоффа.
    
    Использует TradingRange и анализ объёма.
    """
    
    def __init__(
        self,
        volume_ma_period: int = 20,
        climax_volume_mult: float = 2.0,
        spring_depth_atr: float = 0.5,
        test_tolerance_atr: float = 0.5,
        atr_period: int = 14,
    ):
        """
        Параметры:
        ----------
        volume_ma_period : int
            Период скользящей средней объёма.
        climax_volume_mult : float
            Во сколько раз объём должен превышать средний для climax.
        spring_depth_atr : float
            Насколько глубоко (в ATR) Spring/UT выходит за границу range.
        test_tolerance_atr : float
            Допуск (в ATR) для "теста" уровня.
        atr_period : int
            Период ATR.
        """
        self.volume_ma_period = volume_ma_period
        self.climax_volume_mult = climax_volume_mult
        self.spring_depth_atr = spring_depth_atr
        self.test_tolerance_atr = test_tolerance_atr
        self.atr_period = atr_period
    
    def _compute_atr(self, df: pd.DataFrame) -> pd.Series:
        """ATR."""
        high = df['high']
        low = df['low']
        close = df['close']
        prev_close = close.shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ], axis=1).max(axis=1)
        return tr.rolling(window=self.atr_period, min_periods=1).mean()
    
    def _compute_volume_ma(self, df: pd.DataFrame) -> pd.Series:
        """Скользящая средняя объёма."""
        if 'tick_volume' not in df.columns:
            return pd.Series([0] * len(df), index=df.index)
        return df['tick_volume'].rolling(
            window=self.volume_ma_period, min_periods=1
        ).mean()
    
    def _get_window_by_tf(self, df: pd.DataFrame, base: int = 30) -> int:
        """
        Возвращает размер окна в барах в зависимости от ТФ.
        H4: base, D1: base*2, W1: base*3.
        """
        if len(df) < 2:
            return base
        
        import pandas as pd
        try:
            idx = pd.Series(df.index)
            median_delta = idx.diff().median()
            hours = median_delta.total_seconds() / 3600
        except Exception:
            return base
        
        if hours >= 100:
            return base * 3
        elif hours >= 20:
            return base * 2
        else:
            return base
    
    # ============================================================
    # SC - Selling Climax
    # ============================================================
    def find_selling_climax(
        self,
        df: pd.DataFrame,
        r: TradingRange,
    ) -> Optional[WyckoffEvent]:
        """
        SC — кульминация продаж.
        
        Признаки:
        - Резкое падение цены
        - Аномально большой объём (> climax_volume_mult × MA)
        - Цена в нижней части range или ниже
        - Цена закрытия в верхней половине бара (отскок)
        """
        events = []
        atr = self._compute_atr(df)
        vol_ma = self._compute_volume_ma(df)
        
        # Ищем в нижней половине range
        lower_zone = r.lower + (r.upper - r.lower) * 0.5
        
        for i in range(r.start_idx, min(r.end_idx + 1, len(df))):
            row = df.iloc[i]
            if i >= len(vol_ma) or vol_ma.iloc[i] <= 0:
                continue
            
            # Условия
            price_low = row['low']
            close = row['close']
            volume = row['tick_volume'] if 'tick_volume' in df.columns else 0
            vol_ratio = volume / vol_ma.iloc[i]
            
            # В нижней зоне range
            in_lower = price_low <= lower_zone
            # Аномальный объём
            high_vol = vol_ratio >= self.climax_volume_mult
            # Закрытие выше минимума (отскок)
            close_recovery = close > (row['high'] + row['low']) / 2
            
            if in_lower and high_vol and close_recovery:
                events.append(WyckoffEvent(
                    type='SC',
                    idx=i,
                    price=price_low,
                    volume=int(volume),
                    direction='bullish',
                    confidence=min(1.0, vol_ratio / self.climax_volume_mult),
                    meta={'vol_ratio': round(vol_ratio, 2)},
                ))
        
        # Возвращаем только самый сильный
        if events:
            events.sort(key=lambda e: e.volume, reverse=True)
            return events[0]
        return None
    
    # ============================================================
    # AR - Automatic Rally
    # ============================================================
    def find_automatic_rally(
        self,
        df: pd.DataFrame,
        sc: WyckoffEvent,
    ) -> Optional[WyckoffEvent]:
        """
        AR — автоматическое ралли после SC.
        
        Признаки:
        - Идёт после SC
        - Рост цены
        - Постепенное снижение объёма
        """
        if sc is None:
            return None
        
        # Ищем в течение следующих 20 баров
        start = sc.idx + 1
        end = min(sc.idx + 20, len(df))
        
        if start >= end:
            return None
        
        sub = df.iloc[start:end]
        if len(sub) == 0:
            return None
        
        # Максимум ралли
        max_high = sub['high'].max()
        max_idx = sub['high'].idxmax()
        
        # Находим позицию по индексу
        try:
            pos = df.index.get_loc(max_idx)
        except (KeyError, TypeError):
            pos = start
        
        return WyckoffEvent(
            type='AR',
            idx=int(pos),
            price=float(max_high),
            volume=int(df.iloc[pos]['tick_volume']) if 'tick_volume' in df.columns else 0,
            direction='bullish',
            confidence=0.8,
            meta={'sc_idx': sc.idx},
        )
    
    # ============================================================
    # ST - Secondary Test
    # ============================================================
    def find_secondary_test(
        self,
        df: pd.DataFrame,
        sc: WyckoffEvent,
        ar: WyckoffEvent,
    ) -> Optional[WyckoffEvent]:
        """
        ST — вторичный тест минимума SC на сниженном объёме.
        
        Признаки:
        - После AR
        - Цена возвращается к минимуму SC
        - Объём меньше, чем у SC
        """
        if sc is None or ar is None:
            return None
        
        start = ar.idx + 1
        end = min(ar.idx + 30, len(df))
        
        if start >= end:
            return None
        
        atr = self._compute_atr(df)
        tolerance = self.test_tolerance_atr * atr.iloc[sc.idx]
        
        for i in range(start, end):
            row = df.iloc[i]
            if row['low'] <= sc.price + tolerance and row['low'] >= sc.price - tolerance:
                volume = row['tick_volume'] if 'tick_volume' in df.columns else 0
                # ST должен быть на меньшем объёме, чем SC
                if volume < sc.volume:
                    return WyckoffEvent(
                        type='ST',
                        idx=i,
                        price=float(row['low']),
                        volume=int(volume),
                        direction='bullish',
                        confidence=0.7,
                        meta={'sc_idx': sc.idx, 'ar_idx': ar.idx},
                    )
        
        return None
    
    # ============================================================
    # Spring - ложный пробой вниз
    # ============================================================
    def find_spring(
        self,
        df: pd.DataFrame,
        r: TradingRange,
    ) -> Optional[WyckoffEvent]:
        """
        Spring — swing low у нижней границы range.
        """
        vol_ma = self._compute_volume_ma(df)
        lower_zone = r.lower + (r.upper - r.lower) * 0.2
        
        for i in range(r.start_idx + 3, min(r.end_idx - 2, len(df) - 3)):
            row = df.iloc[i]
            
            if row['low'] > lower_zone:
                continue
            
            left_lows = [df.iloc[i - k]['low'] for k in range(1, 4)]
            right_lows = [df.iloc[i + k]['low'] for k in range(1, 4)]
            
            if row['low'] > min(left_lows) or row['low'] > min(right_lows):
                continue
            
            spread = row['high'] - row['low']
            if spread <= 0:
                continue
            close_pos = (row['close'] - row['low']) / spread
            if close_pos < 0.5:
                continue
            
            volume = row['tick_volume'] if 'tick_volume' in df.columns else 0
            vol_ratio = volume / vol_ma.iloc[i] if vol_ma.iloc[i] > 0 else 1
            
            return WyckoffEvent(
                type='Spring',
                idx=i,
                price=float(row['low']),
                volume=int(volume),
                direction='bullish',
                confidence=min(1.0, 0.5 + close_pos * 0.5),
                meta={
                    'range_lower': r.lower,
                    'close_pos': round(close_pos, 2),
                    'vol_ratio': round(vol_ratio, 2),
                },
            )
        
        return None
    # ============================================================
    # Test - повторный тест Spring
    # ============================================================
    def find_test(
        self,
        df: pd.DataFrame,
        spring: WyckoffEvent,
    ) -> Optional[WyckoffEvent]:
        """
        Test — повторный тест уровня Spring на меньшем объёме.
        """
        if spring is None:
            return None
        
        start = spring.idx + 1
        window = self._get_window_by_tf(df, base=30)
        end = min(spring.idx + window, len(df))
        
        if start >= end:
            return None
        
        atr = self._compute_atr(df)
        tolerance = self.test_tolerance_atr * atr.iloc[spring.idx]
        
        for i in range(start, end):
            row = df.iloc[i]
            if abs(row['low'] - spring.price) <= tolerance:
                volume = row['tick_volume'] if 'tick_volume' in df.columns else 0
                if volume < spring.volume * 0.9:
                    return WyckoffEvent(
                        type='Test',
                        idx=i,
                        price=float(row['low']),
                        volume=int(volume),
                        direction='bullish',
                        confidence=0.8,
                        meta={'spring_idx': spring.idx},
                    )
        
        return None
    
    # ============================================================
    # SOS - Sign of Strength
    # ============================================================
    def find_sos(
        self,
        df: pd.DataFrame,
        r: TradingRange,
    ) -> Optional[WyckoffEvent]:
        """
        SOS — знак силы: пробой верхней границы range на объёме.
        """
        atr = self._compute_atr(df)
        vol_ma = self._compute_volume_ma(df)
        
        for i in range(r.start_idx, min(r.end_idx + 30, len(df))):
            row = df.iloc[i]
            
            # Пробой верхней границы
            if row['high'] > r.upper:
                volume = row['tick_volume'] if 'tick_volume' in df.columns else 0
                vol_ratio = volume / vol_ma.iloc[i] if vol_ma.iloc[i] > 0 else 1
                
                # На объёме
                if vol_ratio >= 1.2:
                    return WyckoffEvent(
                        type='SOS',
                        idx=i,
                        price=float(row['high']),
                        volume=int(volume),
                        direction='bullish',
                        confidence=min(1.0, vol_ratio / 1.5),
                        meta={
                            'range_upper': r.upper,
                            'breakout': round(row['high'] - r.upper, 6),
                            'vol_ratio': round(vol_ratio, 2),
                        },
                    )
        
        return None
    
    # ============================================================
    # LPS - Last Point of Support
    # ============================================================
    def find_lps(
        self,
        df: pd.DataFrame,
        sos: WyckoffEvent,
    ) -> Optional[WyckoffEvent]:
        """
        LPS — последняя точка поддержки: откат после SOS,
        который удерживается выше уровня SOS.
        """
        if sos is None:
            return None
        
        start = sos.idx + 1
        end = min(sos.idx + 20, len(df))
        
        if start >= end:
            return None
        
        # Ищем локальный минимум после SOS
        sub = df.iloc[start:end]
        if len(sub) == 0:
            return None
        
        min_low = sub['low'].min()
        min_pos = sub['low'].idxmin()
        
        try:
            pos = df.index.get_loc(min_pos)
        except (KeyError, TypeError):
            pos = start
        
        # LPS должен удержаться выше уровня SOS - отката
        # (не ниже, чем цена SOS минус какой-то допуск)
        if min_low > sos.price * 0.99:
            return WyckoffEvent(
                type='LPS',
                idx=int(pos),
                price=float(min_low),
                volume=int(df.iloc[pos]['tick_volume']) if 'tick_volume' in df.columns else 0,
                direction='bullish',
                confidence=0.75,
                meta={'sos_idx': sos.idx},
            )
        
        return None
    
    # ============================================================
    # UT - Upthrust
    # ============================================================
    def find_upthrust(
        self,
        df: pd.DataFrame,
        r: TradingRange,
    ) -> Optional[WyckoffEvent]:
        """
        UT — swing high у верхней границы range.
        """
        vol_ma = self._compute_volume_ma(df)
        upper_zone = r.upper - (r.upper - r.lower) * 0.2
        
        for i in range(r.start_idx + 3, min(r.end_idx - 2, len(df) - 3)):
            row = df.iloc[i]
            
            if row['high'] < upper_zone:
                continue
            
            left_highs = [df.iloc[i - k]['high'] for k in range(1, 4)]
            right_highs = [df.iloc[i + k]['high'] for k in range(1, 4)]
            
            if row['high'] < max(left_highs) or row['high'] < max(right_highs):
                continue
            
            spread = row['high'] - row['low']
            if spread <= 0:
                continue
            close_pos = (row['close'] - row['low']) / spread
            if close_pos > 0.5:
                continue
            
            volume = row['tick_volume'] if 'tick_volume' in df.columns else 0
            vol_ratio = volume / vol_ma.iloc[i] if vol_ma.iloc[i] > 0 else 1
            
            return WyckoffEvent(
                type='UT',
                idx=i,
                price=float(row['high']),
                volume=int(volume),
                direction='bearish',
                confidence=min(1.0, 0.5 + (1 - close_pos) * 0.5),
                meta={
                    'range_upper': r.upper,
                    'close_pos': round(close_pos, 2),
                    'vol_ratio': round(vol_ratio, 2),
                },
            )
        
        return None
    # ============================================================
    # SOW - Sign of Weakness
    # ============================================================
    def find_sow(
        self,
        df: pd.DataFrame,
        r: TradingRange,
    ) -> Optional[WyckoffEvent]:
        """
        SOW — знак слабости: пробой нижней границы range на объёме.
        """
        vol_ma = self._compute_volume_ma(df)
        
        for i in range(r.start_idx, min(r.end_idx + 30, len(df))):
            row = df.iloc[i]
            
            if row['low'] < r.lower:
                volume = row['tick_volume'] if 'tick_volume' in df.columns else 0
                vol_ratio = volume / vol_ma.iloc[i] if vol_ma.iloc[i] > 0 else 1
                
                if vol_ratio >= 1.2:
                    return WyckoffEvent(
                        type='SOW',
                        idx=i,
                        price=float(row['low']),
                        volume=int(volume),
                        direction='bearish',
                        confidence=min(1.0, vol_ratio / 1.5),
                        meta={
                            'range_lower': r.lower,
                            'vol_ratio': round(vol_ratio, 2),
                        },
                    )
        
        return None
    
    # ============================================================
    # LPSY - Last Point of Supply
    # ============================================================
    def find_lpsy(
        self,
        df: pd.DataFrame,
        sow: WyckoffEvent,
    ) -> Optional[WyckoffEvent]:
        """
        LPSY — последняя точка предложения: отскок после SOW,
        который не может пробить уровень SOW.
        """
        if sow is None:
            return None
        
        start = sow.idx + 1
        end = min(sow.idx + 20, len(df))
        
        if start >= end:
            return None
        
        sub = df.iloc[start:end]
        if len(sub) == 0:
            return None
        
        max_high = sub['high'].max()
        max_pos = sub['high'].idxmax()
        
        try:
            pos = df.index.get_loc(max_pos)
        except (KeyError, TypeError):
            pos = start
        
        # LPSY должен быть ниже уровня SOW
        if max_high < sow.price * 1.01:
            return WyckoffEvent(
                type='LPSY',
                idx=int(pos),
                price=float(max_high),
                volume=int(df.iloc[pos]['tick_volume']) if 'tick_volume' in df.columns else 0,
                direction='bearish',
                confidence=0.75,
                meta={'sow_idx': sow.idx},
            )
        
        return None
    
    # ============================================================
    # Полный анализ
    # ============================================================
    def detect_all(
        self,
        df: pd.DataFrame,
        r: TradingRange,
    ) -> List[WyckoffEvent]:
        """
        Находит все события в range.
        """
        events = []
        
        # SC → AR → ST
        sc = self.find_selling_climax(df, r)
        if sc is not None:
            events.append(sc)
            ar = self.find_automatic_rally(df, sc)
            if ar is not None:
                events.append(ar)
                st = self.find_secondary_test(df, sc, ar)
                if st is not None:
                    events.append(st)
        
        # Spring → Test
        spring = self.find_spring(df, r)
        if spring:
            events.append(spring)
            test = self.find_test(df, spring)
            if test:
                events.append(test)
        
        # SOS → LPS
        sos = self.find_sos(df, r)
        if sos:
            events.append(sos)
            lps = self.find_lps(df, sos)
            if lps:
                events.append(lps)
        
        # UT
        ut = self.find_upthrust(df, r)
        if ut:
            events.append(ut)
        
        # SOW → LPSY
        sow = self.find_sow(df, r)
        if sow:
            events.append(sow)
            lpsy = self.find_lpsy(df, sow)
            if lpsy:
                events.append(lpsy)
        
        # Сортируем по idx
        events.sort(key=lambda e: e.idx)
        return events