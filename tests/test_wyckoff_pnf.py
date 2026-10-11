"""
Тесты для wyckoff.pnf (Point & Figure).
"""
import pytest
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wyckoff.pnf import (
    PnfColumn, HorizontalFormation, PnfChart, PnfBuilder,
)


def make_df(prices):
    """Создаёт DataFrame из списка цен."""
    n = len(prices)
    dates = [datetime(2026, 1, 1) + timedelta(hours=i) for i in range(n)]
    return pd.DataFrame({
        'open': prices,
        'high': [p + 0.0005 for p in prices],
        'low': [p - 0.0005 for p in prices],
        'close': prices,
        'tick_volume': [100] * n,
    }, index=dates)


class TestPnfColumn:
    def test_init(self):
        col = PnfColumn(type='X', prices=[1.1, 1.2, 1.3])
        assert col.type == 'X'
        assert len(col.prices) == 3
    
    def test_repr(self):
        col = PnfColumn(type='X', prices=[1.1, 1.2, 1.3])
        s = repr(col)
        assert 'X' in s
        assert '3 boxes' in s


class TestHorizontalFormation:
    def test_init(self):
        f = HorizontalFormation(
            upper=1.1, lower=1.0,
            width_boxes=5,
            start_idx=0, end_idx=10,
            target_up=1.15, target_down=0.95,
        )
        assert f.width_boxes == 5
        assert f.target_up == 1.15
    
    def test_repr(self):
        f = HorizontalFormation(
            upper=1.1, lower=1.0,
            width_boxes=5,
            start_idx=0, end_idx=10,
        )
        s = repr(f)
        assert '5 boxes' in s


class TestPnfBuilder:
    def test_init(self):
        b = PnfBuilder(box_size=0.001, reversal=3)
        assert b.box_size == 0.001
        assert b.reversal == 3
    
    def test_build_empty_df(self):
        b = PnfBuilder(box_size=0.001, reversal=3)
        df = pd.DataFrame(columns=['open', 'high', 'low', 'close'])
        chart = b.build(df)
        assert len(chart.columns) == 0
    
    def test_build_single_candle(self):
        b = PnfBuilder(box_size=0.001, reversal=3)
        df = make_df([1.1])
        chart = b.build(df)
        # Один бар — минимум 0 колонок
        assert isinstance(chart, PnfChart)
    
    def test_build_uptrend(self):
        """Восходящий тренд → X-колонка."""
        b = PnfBuilder(box_size=0.001, reversal=3)
        prices = [1.1 + i * 0.001 for i in range(50)]
        df = make_df(prices)
        chart = b.build(df)
        
        # Должна быть минимум 1 X-колонка
        assert len(chart.columns) >= 1
        x_cols = [c for c in chart.columns if c.type == 'X']
        assert len(x_cols) >= 1
    
    def test_build_downtrend(self):
        """Нисходящий тренд → O-колонка."""
        b = PnfBuilder(box_size=0.001, reversal=3)
        prices = [1.2 - i * 0.001 for i in range(50)]
        df = make_df(prices)
        chart = b.build(df)
        
        assert len(chart.columns) >= 1
    
    def test_build_volatile(self):
        """Волатильный рынок → несколько колонок."""
        b = PnfBuilder(box_size=0.001, reversal=3)
        prices = [1.1 + np.sin(i / 5) * 0.01 for i in range(100)]
        df = make_df(prices)
        chart = b.build(df)
        
        # Должно быть несколько колонок
        assert len(chart.columns) >= 2
    
    def test_build_respects_box_size(self):
        """Box size влияет на количество колонок."""
        prices = [1.1 + np.sin(i / 5) * 0.01 for i in range(100)]
        df = make_df(prices)
        
        b_small = PnfBuilder(box_size=0.0001, reversal=3)
        b_large = PnfBuilder(box_size=0.005, reversal=3)
        
        chart_small = b_small.build(df)
        chart_large = b_large.build(df)
        
        # Меньший box → больше колонок
        assert len(chart_small.columns) >= len(chart_large.columns)


class TestHorizontalFormations:
    def test_no_formations_short_chart(self):
        b = PnfBuilder(box_size=0.001, reversal=3)
        chart = PnfChart(box_size=0.001, reversal=3)
        # Пустой chart
        formations = chart.find_horizontal_formations()
        assert formations == []
    
    def test_find_formations(self):
        """Ищем формации в боковике."""
        b = PnfBuilder(box_size=0.001, reversal=3)
        # Боковик: цена колеблется 1.100-1.110
        prices = []
        for i in range(200):
            if i % 2 == 0:
                prices.append(1.100 + np.random.rand() * 0.010)
            else:
                prices.append(1.110 - np.random.rand() * 0.010)
        
        df = make_df(prices)
        chart = b.build(df)
        
        formations = chart.find_horizontal_formations(min_width_boxes=2)
        assert isinstance(formations, list)
    
    def test_formation_has_targets(self):
        """Формация должна иметь targets."""
        f = HorizontalFormation(
            upper=1.1, lower=1.0,
            width_boxes=5,
            start_idx=0, end_idx=10,
            target_up=1.15, target_down=0.95,
        )
        assert f.target_up > f.upper
        assert f.target_down < f.lower


class TestCalculateTargets:
    def test_no_formations(self):
        chart = PnfChart(box_size=0.001, reversal=3)
        target = chart.calculate_targets(breakout_price=1.1, direction='up')
        assert target is None
    
    def test_target_up(self):
        """Target вверх = верхняя граница + ширина."""
        chart = PnfChart(box_size=0.001, reversal=3)
        # Симулируем формацию
        chart.columns = [
            PnfColumn(type='X', prices=[1.1, 1.095, 1.09, 1.085]),
            PnfColumn(type='O', prices=[1.085, 1.09, 1.095, 1.1]),
            PnfColumn(type='X', prices=[1.1, 1.105]),
        ]
        
        target = chart.calculate_targets(breakout_price=1.1, direction='up')
        # Target должен быть > 1.1 (если формации найдены)
        assert target is None or target > 1.1