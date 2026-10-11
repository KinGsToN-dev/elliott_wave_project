"""
Point & Figure (P&F) Chart — по книге Villahermosa (стр. 56-59).

P&F показывает только ЦЕНУ, игнорируя время.
- X-колонка: рост на N box.
- O-колонка: падение на N box.
- Reversal: сколько box нужно для разворота.

Задачи:
- Горизонтальные формации (ширина = цель).
- Расчёт targets по ширине формации.
- Law of Cause & Effect: bigger formation → bigger move.

Использование:
    builder = PnfBuilder(box_size=0.001, reversal=3)
    chart = builder.build(df)
    
    # Горизонтальные формации
    formations = chart.find_horizontal_formations()
    
    # Target по формации
    target = chart.calculate_targets(breakout_price=1.1, direction='up')
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class PnfColumn:
    """Колонка P&F."""
    type: str              # 'X' или 'O'
    prices: List[float]    # список цен (сверху вниз для X, снизу вверх для O)
    start_idx: int = 0     # индекс начала в df
    
    def __repr__(self):
        return f"PnfColumn({self.type}, {len(self.prices)} boxes, {self.prices[0]:.5f}-{self.prices[-1]:.5f})"


@dataclass
class HorizontalFormation:
    """Горизонтальная формация P&F."""
    upper: float           # верхняя граница
    lower: float           # нижняя граница
    width_boxes: int       # ширина в box
    start_idx: int
    end_idx: int
    target_up: float = 0.0    # цель вверх
    target_down: float = 0.0  # цель вниз
    
    def __repr__(self):
        return (f"HorizontalFormation([{self.lower:.5f}, {self.upper:.5f}], "
                f"{self.width_boxes} boxes, target_up={self.target_up:.5f})")


class PnfChart:
    """P&F Chart."""
    
    def __init__(self, box_size: float = 0.001, reversal: int = 3):
        self.box_size = box_size
        self.reversal = reversal
        self.columns: List[PnfColumn] = []
    
    def add_to_current_column(self, price: float, col_type: str):
        """Добавляет цену в текущую колонку."""
        if not self.columns:
            return
        
        current = self.columns[-1]
        if current.type != col_type:
            return
        
        # X-колонка: цена растёт
        if col_type == 'X':
            if price > current.prices[0]:
                current.prices.insert(0, price)
            elif price < current.prices[-1]:
                # Не должно произойти
                pass
        else:  # 'O'
            if price < current.prices[0]:
                current.prices.insert(0, price)
    
    def new_column(self, price: float, col_type: str):
        """Создаёт новую колонку."""
        self.columns.append(PnfColumn(
            type=col_type,
            prices=[price],
            start_idx=0,
        ))
    
    def find_horizontal_formations(
        self,
        min_width_boxes: int = 3,
    ) -> List[HorizontalFormation]:
        """
        Находит горизонтальные формации.
        
        Формация — это зона, где несколько колонок X и O пересекаются.
        Ширина = количество колонок в этой зоне.
        """
        if len(self.columns) < 3:
            return []
        
        formations = []
        
        # Проходим по всем ценам (box levels)
        all_prices = set()
        for col in self.columns:
            for p in col.prices:
                all_prices.add(round(p, 6))
        
        sorted_prices = sorted(all_prices, reverse=True)
        
        for i in range(len(sorted_prices) - 1):
            upper = sorted_prices[i]
            lower = sorted_prices[i + 1]
            
            # Считаем, сколько колонок пересекает эту зону
            width = 0
            for col in self.columns:
                min_p = min(col.prices)
                max_p = max(col.prices)
                
                if min_p <= lower and max_p >= upper:
                    width += 1
            
            if width >= min_width_boxes:
                target_range = width * self.box_size
                formations.append(HorizontalFormation(
                    upper=upper,
                    lower=lower,
                    width_boxes=width,
                    start_idx=0,
                    end_idx=len(self.columns) - 1,
                    target_up=upper + target_range,
                    target_down=lower - target_range,
                ))
        
        # Убираем дубликаты (по верхней границе)
        seen = set()
        unique = []
        for f in formations:
            key = round(f.upper, 6)
            if key not in seen:
                seen.add(key)
                unique.append(f)
        
        return unique
    
    def calculate_targets(
        self,
        breakout_price: float,
        direction: str = 'up',
    ) -> Optional[float]:
        """
        Считает target по ширине формации.
        
        Параметры:
        ----------
        breakout_price : float
            Цена пробоя.
        direction : str
            'up' или 'down'.
        
        Возвращает:
        -----------
        Target price или None.
        """
        formations = self.find_horizontal_formations(min_width_boxes=3)
        
        if not formations:
            return None
        
        # Ищем формацию, ближайшую к цене пробоя
        best = None
        min_dist = float('inf')
        
        for f in formations:
            dist = abs(f.upper - breakout_price)
            if dist < min_dist:
                min_dist = dist
                best = f
        
        if best is None:
            return None
        
        if direction == 'up':
            return best.target_up
        else:
            return best.target_down


class PnfBuilder:
    """Построение P&F из OHLC."""
    
    def __init__(
        self,
        box_size: float = 0.001,
        reversal: int = 3,
        use_close: bool = False,
    ):
        """
        Параметры:
        ----------
        box_size : float
            Размер box (минимум 1 пипс).
        reversal : int
            Сколько box для разворота (обычно 3).
        use_close : bool
            Использовать close (True) или high/low (False).
        """
        self.box_size = box_size
        self.reversal = reversal
        self.use_close = use_close
    
    def _round_to_box(self, price: float) -> float:
        """Округляет цену до ближайшего box."""
        return round(price / self.box_size) * self.box_size
    
    def build(self, df: pd.DataFrame) -> PnfChart:
        """
        Строит P&F chart из OHLC.
        
        Алгоритм:
        1. Начинаем с первой цены.
        2. Если цена выросла на >= box_size → X.
        3. Если упала на >= reversal * box_size → новая O-колонка.
        4. И наоборот.
        """
        if df is None or len(df) < 2:
            return PnfChart(self.box_size, self.reversal)
        
        chart = PnfChart(self.box_size, self.reversal)
        
        # Начинаем с первой цены
        first_price = self._round_to_box(df.iloc[0]['close'])
        
        # Определяем первое направление
        # Смотрим на high/low первого бара
        if self.use_close:
            prices = df['close'].values
        else:
            # Используем high и low
            prices = df['close'].values  # упрощённо
        
        # Начинаем X-колонку
        chart.new_column(first_price, 'X')
        
        current_extreme = first_price
        current_type = 'X'
        
        for i in range(1, len(df)):
            row = df.iloc[i]
            
            if self.use_close:
                high = self._round_to_box(row['close'])
                low = self._round_to_box(row['close'])
            else:
                high = self._round_to_box(row['high'])
                low = self._round_to_box(row['low'])
            
            if current_type == 'X':
                # X-колонка: реагирует на рост
                if high > current_extreme:
                    # Добавляем X от current_extreme + box до high
                    steps = int((high - current_extreme) / self.box_size)
                    for s in range(1, steps + 1):
                        new_price = current_extreme + s * self.box_size
                        chart.columns[-1].prices.insert(0, round(new_price, 6))
                    current_extreme = high
                
                # Проверяем разворот вниз
                if current_extreme - low >= self.reversal * self.box_size:
                    # Новая O-колонка
                    new_low = current_extreme - self.reversal * self.box_size
                    steps = int((current_extreme - low) / self.box_size)
                    chart.new_column(round(current_extreme - self.box_size, 6), 'O')
                    for s in range(2, steps + 1):
                        new_price = current_extreme - s * self.box_size
                        chart.columns[-1].prices.insert(0, round(new_price, 6))
                    current_extreme = round(current_extreme - steps * self.box_size, 6)
                    current_type = 'O'
            
            else:  # 'O'
                # O-колонка: реагирует на падение
                if low < current_extreme:
                    steps = int((current_extreme - low) / self.box_size)
                    for s in range(1, steps + 1):
                        new_price = current_extreme - s * self.box_size
                        chart.columns[-1].prices.insert(0, round(new_price, 6))
                    current_extreme = low
                
                # Разворот вверх
                if high - current_extreme >= self.reversal * self.box_size:
                    steps = int((high - current_extreme) / self.box_size)
                    chart.new_column(round(current_extreme + self.box_size, 6), 'X')
                    for s in range(2, steps + 1):
                        new_price = current_extreme + s * self.box_size
                        chart.columns[-1].prices.insert(0, round(new_price, 6))
                    current_extreme = round(current_extreme + steps * self.box_size, 6)
                    current_type = 'X'
        
        return chart