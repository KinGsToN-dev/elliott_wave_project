"""
Wyckoff Trendlines - линии тренда.

4 основные линии (по книге Хатсона, стр. 38-43):

1. Support line   - восходящая, через 2 минимума
2. Supply line    - нисходящая, через 2 максимума
3. Overbought line - параллельно support, через максимум между точками support
4. Oversold line  - параллельно supply, через минимум между точками supply

Использует pivots из core.zigzag.
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.zigzag import ZigZag


class LineType(Enum):
    """Тип линии тренда."""
    SUPPORT = 'support'         # поддержка (восходящая)
    SUPPLY = 'supply'           # предложение (нисходящая)
    OVERBOUGHT = 'overbought'   # перекупленность (параллельно support)
    OVERSOLD = 'oversold'       # перепроданность (параллельно supply)


@dataclass
class Trendline:
    """
    Линия тренда.
    
    y = slope * x + intercept
    """
    type: LineType
    x1: int             # индекс первой точки
    y1: float           # цена первой точки
    x2: int             # индекс второй точки
    y2: float           # цена второй точки
    slope: float = 0.0
    intercept: float = 0.0
    touches: int = 0    # сколько раз цена касалась
    is_active: bool = True
    
    def __post_init__(self):
        if self.x2 != self.x1:
            self.slope = (self.y2 - self.y1) / (self.x2 - self.x1)
        else:
            self.slope = 0.0
        self.intercept = self.y1 - self.slope * self.x1
    
    def get_value(self, x: int) -> float:
        """Значение y в точке x."""
        return self.slope * x + self.intercept
    
    def __repr__(self):
        return (
            f"Trendline({self.type.value}, "
            f"x=[{self.x1},{self.x2}], slope={self.slope:.6f}, "
            f"touches={self.touches})"
        )


@dataclass
class TrendlineBreak:
    """Пробой линии тренда."""
    line: Trendline
    idx: int            # индекс бара пробоя
    price: float        # цена пробоя
    direction: str      # 'up' (вверх) или 'down' (вниз)
    volume: int
    strength: float     # 0..1
    meta: dict = field(default_factory=dict)
    
    def __repr__(self):
        return (
            f"TrendlineBreak({self.line.type.value} @ idx={self.idx}, "
            f"dir={self.direction}, str={self.strength:.2f})"
        )


class TrendlineDetector:
    """
    Детектор линий тренда и их пробоев.
    """
    
    def __init__(
        self,
        zigzag_length: int = 5,
        min_pivots: int = 4,
        touch_tolerance_atr: float = 0.3,
        break_confirmation_atr: float = 0.2,
    ):
        """
        Параметры:
        ----------
        zigzag_length : int
            Длина ZigZag (передаётся в core.zigzag).
        min_pivots : int
            Минимум pivots для построения.
        touch_tolerance_atr : float
            Допуск касания линии (в ATR).
        break_confirmation_atr : float
            Минимальный пробой для подтверждения (в ATR).
        """
        self.zigzag_length = zigzag_length
        self.min_pivots = min_pivots
        self.touch_tolerance_atr = touch_tolerance_atr
        self.break_confirmation_atr = break_confirmation_atr
    
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
        return tr.rolling(window=14, min_periods=1).mean()
    
    def _find_pivots(
        self,
        df: pd.DataFrame,
    ) -> Tuple[List[Tuple[int, float]], List[Tuple[int, float]]]:
        """
        Находит pivots через ZigZag.
        
        ZigZag.find_pivots() возвращает DataFrame:
            price  type
        time
        4      5  high
        ...
        
        Мы мапим timestamp обратно в позицию (int) в df.
        
        Возвращает (lows, highs) — списки (idx, price).
        """
        try:
            zz = ZigZag(df, length=self.zigzag_length)
            pivots = zz.find_pivots()
        except Exception as e:
            print(f"[WARN] ZigZag error: {e}")
            return [], []
        
        if pivots is None:
            return [], []
        
        # DataFrame (основной формат)
        if isinstance(pivots, pd.DataFrame):
            if pivots.empty:
                return [], []
            
            # Проверяем колонки
            if 'price' not in pivots.columns or 'type' not in pivots.columns:
                return [], []
            
            # Создаём маппинг timestamp → позиция в df
            # (на случай, если индекс pivots — это time)
            idx_to_pos = {}
            if hasattr(df.index, '__iter__'):
                for pos, ts in enumerate(df.index):
                    idx_to_pos[ts] = pos
            
            lows = []
            highs = []
            
            for ts, row in pivots.iterrows():
                price = float(row['price'])
                ptype = str(row['type']).lower()
                
                # Мапим timestamp в позицию
                pos = idx_to_pos.get(ts)
                if pos is None:
                    # Fallback: если индекс — уже число
                    try:
                        pos = int(ts)
                    except (ValueError, TypeError):
                        continue
                
                if 'low' in ptype:
                    lows.append((pos, price))
                elif 'high' in ptype:
                    highs.append((pos, price))
            
            return lows, highs
        
        # Список (на будущее, если ZigZag изменится)
        if isinstance(pivots, (list, tuple)):
            lows = []
            highs = []
            for p in pivots:
                if isinstance(p, dict):
                    idx = p.get('index', p.get('idx'))
                    price = p.get('price')
                    ptype = str(p.get('type', '')).lower()
                elif isinstance(p, (tuple, list)) and len(p) >= 2:
                    idx, price = p[0], p[1]
                    ptype = str(p[2]).lower() if len(p) >= 3 else ''
                else:
                    continue
                
                if idx is None or price is None:
                    continue
                
                try:
                    idx = int(idx)
                    price = float(price)
                except (ValueError, TypeError):
                    continue
                
                if 'low' in ptype:
                    lows.append((idx, price))
                elif 'high' in ptype:
                    highs.append((idx, price))
            
            return lows, highs
        
        return [], []

    
    def _count_touches(
        self,
        df: pd.DataFrame,
        line: Trendline,
        tolerance: float,
    ) -> int:
        """Считает касания линии."""
        touches = 0
        for i in range(line.x1, min(line.x2 + 20, len(df))):
            expected = line.get_value(i)
            row = df.iloc[i]
            
            if line.type in (LineType.SUPPORT, LineType.OVERSOLD):
                # Для низа
                if abs(row['low'] - expected) <= tolerance:
                    touches += 1
            else:
                # Для верха
                if abs(row['high'] - expected) <= tolerance:
                    touches += 1
        
        return touches
    
    def find_support_line(
        self,
        df: pd.DataFrame,
        lows: List[Tuple[int, float]],
    ) -> Optional[Trendline]:
        """
        Support line — через два последовательных минимума.
        Восходящая (slope > 0).
        """
        if len(lows) < 2:
            return None
        
        # Ищем восходящие (второй low выше первого)
        for i in range(len(lows) - 1, 0, -1):
            x1, y1 = lows[i - 1]
            x2, y2 = lows[i]
            if y2 > y1:
                return Trendline(
                    type=LineType.SUPPORT,
                    x1=x1, y1=y1, x2=x2, y2=y2,
                )
        
        return None
    
    def find_supply_line(
        self,
        df: pd.DataFrame,
        highs: List[Tuple[int, float]],
    ) -> Optional[Trendline]:
        """
        Supply line — через два последовательных максимума.
        Нисходящая (slope < 0).
        """
        if len(highs) < 2:
            return None
        
        for i in range(len(highs) - 1, 0, -1):
            x1, y1 = highs[i - 1]
            x2, y2 = highs[i]
            if y2 < y1:
                return Trendline(
                    type=LineType.SUPPLY,
                    x1=x1, y1=y1, x2=x2, y2=y2,
                )
        
        return None
    
    def find_overbought_line(
        self,
        df: pd.DataFrame,
        support: Trendline,
        highs: List[Tuple[int, float]],
    ) -> Optional[Trendline]:
        """
        Overbought line — параллельно support, через первый максимум
        между двумя точками support.
        """
        if support is None:
            return None
        
        # Ищем максимум между x1 и x2 support
        candidates = [
            (idx, price) for idx, price in highs
            if support.x1 <= idx <= support.x2
        ]
        
        if not candidates:
            return None
        
        # Берём первый
        x_anchor, y_anchor = candidates[0]
        
        # Параллельно support: тот же slope, через anchor
        # Сдвигаем x1, x2 support так, чтобы линия прошла через anchor
        new_y1 = y_anchor - support.slope * (x_anchor - support.x1)
        
        return Trendline(
            type=LineType.OVERBOUGHT,
            x1=support.x1,
            y1=support.y1 + (new_y1 - support.y1),
            x2=support.x2,
            y2=support.y2 + (new_y1 - support.y1),
        )
    
    def find_oversold_line(
        self,
        df: pd.DataFrame,
        supply: Trendline,
        lows: List[Tuple[int, float]],
    ) -> Optional[Trendline]:
        """
        Oversold line — параллельно supply, через первый минимум
        между двумя точками supply.
        """
        if supply is None:
            return None
        
        candidates = [
            (idx, price) for idx, price in lows
            if supply.x1 <= idx <= supply.x2
        ]
        
        if not candidates:
            return None
        
        x_anchor, y_anchor = candidates[0]
        new_y1 = y_anchor - supply.slope * (x_anchor - supply.x1)
        
        return Trendline(
            type=LineType.OVERSOLD,
            x1=supply.x1,
            y1=supply.y1 + (new_y1 - supply.y1),
            x2=supply.x2,
            y2=supply.y2 + (new_y1 - supply.y1),
        )
    
    def detect_all(
        self,
        df: pd.DataFrame,
    ) -> List[Trendline]:
        """Находит все линии тренда."""
        if df is None or len(df) < 20:
            return []
        
        lows, highs = self._find_pivots(df)
        
        if len(lows) < 2 and len(highs) < 2:
            return []
        
        lines = []
        
        # Support
        support = self.find_support_line(df, lows)
        if support:
            lines.append(support)
        
        # Supply
        supply = self.find_supply_line(df, highs)
        if supply:
            lines.append(supply)
        
        # Overbought (параллельно support)
        overbought = self.find_overbought_line(df, support, highs)
        if overbought:
            lines.append(overbought)
        
        # Oversold (параллельно supply)
        oversold = self.find_oversold_line(df, supply, lows)
        if oversold:
            lines.append(oversold)
        
        # Считаем касания
        atr = self._compute_atr(df).mean()
        tolerance = self.touch_tolerance_atr * atr if atr > 0 else 0.001
        
        for line in lines:
            line.touches = self._count_touches(df, line, tolerance)
        
        return lines
    
    def detect_break(
        self,
        df: pd.DataFrame,
        line: Trendline,
        start_idx: int = 0,
    ) -> Optional[TrendlineBreak]:
        """
        Ищет пробой линии тренда.
        """
        if line is None:
            return None
        
        atr = self._compute_atr(df)
        avg_atr = atr.iloc[line.x1:min(line.x2 + 20, len(df))].mean()
        break_threshold = self.break_confirmation_atr * avg_atr if avg_atr > 0 else 0.0001
        
        # Ищем от x2 вперёд
        for i in range(max(line.x2 + 1, start_idx), len(df)):
            row = df.iloc[i]
            expected = line.get_value(i)
            
            # Пробой вверх (для supply/overbought) или вниз (для support/oversold)
            if line.type in (LineType.SUPPORT, LineType.OVERSOLD):
                # Support пробивается вниз
                if row['low'] < expected - break_threshold:
                    volume = row['tick_volume'] if 'tick_volume' in df.columns else 0
                    return TrendlineBreak(
                        line=line,
                        idx=i,
                        price=float(row['low']),
                        direction='down',
                        volume=int(volume),
                        strength=min(1.0, abs(row['low'] - expected) / (2 * avg_atr)),
                        meta={'expected': float(expected), 'atr': float(avg_atr)},
                    )
            else:
                # Supply/Overbought пробивается вверх
                if row['high'] > expected + break_threshold:
                    volume = row['tick_volume'] if 'tick_volume' in df.columns else 0
                    return TrendlineBreak(
                        line=line,
                        idx=i,
                        price=float(row['high']),
                        direction='up',
                        volume=int(volume),
                        strength=min(1.0, abs(row['high'] - expected) / (2 * avg_atr)),
                        meta={'expected': float(expected), 'atr': float(avg_atr)},
                    )
        
        return None
    
    def detect_all_breaks(
        self,
        df: pd.DataFrame,
        lines: Optional[List[Trendline]] = None,
    ) -> List[TrendlineBreak]:
        """Находит все пробои."""
        if lines is None:
            lines = self.detect_all(df)
        
        breaks = []
        for line in lines:
            b = self.detect_break(df, line)
            if b is not None:
                breaks.append(b)
        
        breaks.sort(key=lambda x: x.idx)
        return breaks