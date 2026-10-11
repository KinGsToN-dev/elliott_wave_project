"""
Trading Range - определение боковика по методу Вайкоффа.

Trading Range — это область, где цена движется боком,
формируя причину для будущего движения (закон Cause & Effect).

Ключевые параметры:
- Верхняя граница (Resistance)
- Нижняя граница (Support)
- Количество баров
- Ширина (в ATR)
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TradingRange:
    """Trading Range (боковик)."""
    start_idx: int              # Индекс начала
    end_idx: int                # Индекс конца
    upper: float                # Верхняя граница (resistance)
    lower: float                # Нижняя граница (support)
    width: float                # Абсолютная ширина
    width_atr: float            # Ширина в ATR
    bars_count: int             # Количество баров
    start_time: Optional[pd.Timestamp] = None
    end_time: Optional[pd.Timestamp] = None
    touches_upper: int = 0      # Сколько раз цена касалась верхней границы
    touches_lower: int = 0      # Сколько раз цена касалась нижней границы
    
    def __repr__(self):
        return (
            f"TradingRange(bars={self.bars_count}, "
            f"upper={self.upper:.5f}, lower={self.lower:.5f}, "
            f"width_atr={self.width_atr:.2f}, "
            f"touches={self.touches_upper}/{self.touches_lower})"
        )


class TradingRangeDetector:
    """
    Детектор Trading Range.
    
    Алгоритм:
    1. Считаем ATR для нормализации ширины.
    2. Скользящим окном ищем участки, где:
       - диапазон цен (max-min) не превышает max_width_atr * ATR
       - минимум min_bars баров
       - цена касается верхней и нижней границы хотя бы по разу
    3. Расширяем диапазон влево и вправо, пока условие выполняется.
    4. Возвращаем список найденных range.
    """
    
    def __init__(
        self,
        min_bars: int = 20,
        max_width_atr: float = 3.0,
        atr_period: int = 14,
        touch_tolerance_atr: float = 0.3,
    ):
        """
        Параметры:
        ----------
        min_bars : int
            Минимальное количество баров в боковике.
        max_width_atr : float
            Максимальная ширина боковика в ATR.
        atr_period : int
            Период ATR.
        touch_tolerance_atr : float
            Допуск для "касания" границы (в ATR).
        """
        self.min_bars = min_bars
        self.max_width_atr = max_width_atr
        self.atr_period = atr_period
        self.touch_tolerance_atr = touch_tolerance_atr
    
    def _compute_atr(self, df: pd.DataFrame) -> pd.Series:
        """ATR (Average True Range)."""
        high = df['high']
        low = df['low']
        close = df['close']
        
        prev_close = close.shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ], axis=1).max(axis=1)
        
        atr = tr.rolling(window=self.atr_period, min_periods=1).mean()
        return atr
    
    def _count_touches(
        self,
        df: pd.DataFrame,
        upper: float,
        lower: float,
        tolerance: float,
    ) -> tuple:
        """Считает касания верхней и нижней границ."""
        touches_upper = int(
            (df['high'] >= upper - tolerance).sum()
        )
        touches_lower = int(
            (df['low'] <= lower + tolerance).sum()
        )
        return touches_upper, touches_lower
    
    def _find_one_range(
        self,
        df: pd.DataFrame,
        atr: pd.Series,
        start_idx: int,
    ) -> Optional[TradingRange]:
        """
        Пытается найти range, начиная с start_idx.
        Расширяет окно вправо, пока ширина не превышает лимит.
        """
        n = len(df)
        if start_idx >= n - self.min_bars:
            return None
        
        # Инициализация
        upper = df['high'].iloc[start_idx]
        lower = df['low'].iloc[start_idx]
        end_idx = start_idx
        
        # Расширяем вправо
        for i in range(start_idx + 1, n):
            new_upper = max(upper, df['high'].iloc[i])
            new_lower = min(lower, df['low'].iloc[i])
            new_width = new_upper - new_lower
            cur_atr = atr.iloc[i]
            
            if cur_atr <= 0:
                break
            
            if new_width > self.max_width_atr * cur_atr:
                break
            
            upper = new_upper
            lower = new_lower
            end_idx = i
        
        bars_count = end_idx - start_idx + 1
        if bars_count < self.min_bars:
            return None
        
        width = upper - lower
        avg_atr = atr.iloc[start_idx:end_idx + 1].mean()
        width_atr = width / avg_atr if avg_atr > 0 else 0
        
        # Проверяем касания
        sub_df = df.iloc[start_idx:end_idx + 1]
        tolerance = self.touch_tolerance_atr * avg_atr
        touches_upper, touches_lower = self._count_touches(
            sub_df, upper, lower, tolerance
        )
        
        # Должно быть хотя бы по одному касанию каждой границы
        if touches_upper < 1 or touches_lower < 1:
            return None
        
        return TradingRange(
            start_idx=start_idx,
            end_idx=end_idx,
            upper=upper,
            lower=lower,
            width=width,
            width_atr=width_atr,
            bars_count=bars_count,
            start_time=df.index[start_idx] if hasattr(df.index, '__getitem__') else None,
            end_time=df.index[end_idx] if hasattr(df.index, '__getitem__') else None,
            touches_upper=touches_upper,
            touches_lower=touches_lower,
        )
    
    def find_ranges(self, df: pd.DataFrame) -> List[TradingRange]:
        """
        Находит все Trading Range в DataFrame.
        
        Параметры:
        ----------
        df : pd.DataFrame
            Должен содержать колонки 'high', 'low', 'close'.
        
        Возвращает:
        -----------
        List[TradingRange]
        """
        if df is None:
            return []
        
        required = {'high', 'low', 'close'}
        if not required.issubset(df.columns):
            raise ValueError(f"DataFrame должен содержать колонки: {required}")
        
        if df is None or len(df) < self.min_bars:
                    return []


        atr = self._compute_atr(df)
        ranges = []
        i = 0
        n = len(df)
        
        while i < n - self.min_bars:
            r = self._find_one_range(df, atr, i)
            if r is not None:
                ranges.append(r)
                # Прыгаем за конец найденного range,
                # чтобы не находить вложенные
                i = r.end_idx + 1
            else:
                i += 1
        
        return ranges
    
    def get_current_range(
        self,
        df: pd.DataFrame,
    ) -> Optional[TradingRange]:
        """
        Возвращает range, в котором находится последний бар.
        """
        ranges = self.find_ranges(df)
        if not ranges:
            return None
        
        last_idx = len(df) - 1
        for r in ranges:
            if r.start_idx <= last_idx <= r.end_idx:
                return r
        
        return None
    
    def is_price_in_range(
        self,
        price: float,
        r: TradingRange,
        tolerance: float = 0.0,
    ) -> bool:
        """Проверяет, находится ли цена внутри range."""
        return (r.lower - tolerance) <= price <= (r.upper + tolerance)
    
    def get_position_in_range(
        self,
        price: float,
        r: TradingRange,
    ) -> float:
        """
        Возвращает позицию цены в range от 0 до 1.
        0.0 — на нижней границе, 1.0 — на верхней.
        """
        if r.width <= 0:
            return 0.5
        pos = (price - r.lower) / r.width
        return max(0.0, min(1.0, pos))