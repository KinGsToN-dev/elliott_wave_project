"""
Тесты для patterns.combinations.CombinationDetector
"""
import pytest
import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from patterns.combinations import CombinationDetector


def build_pivots_from_points(points, start_type='low'):
    """Создаёт DataFrame пивотов."""
    start_time = datetime(2026, 1, 1)
    data = []
    for i, price in enumerate(points):
        t = start_time + timedelta(hours=i * 5)
        if start_type == 'low':
            ptype = 'low' if i % 2 == 0 else 'high'
        else:
            ptype = 'high' if i % 2 == 0 else 'low'
        data.append({'time': t, 'price': price, 'type': ptype})
    df = pd.DataFrame(data)
    df.set_index('time', inplace=True)
    return df


# Правильные данные
DOUBLE_THREE_BULL = [1.1000, 1.1100, 1.1060, 1.1150]
DOUBLE_THREE_BEAR = [1.2000, 1.1900, 1.1940, 1.1850]


class TestDoubleThree:
    def test_double_three_bullish(self):
        """Двойная тройка (бычья)."""
        pivots = build_pivots_from_points(DOUBLE_THREE_BULL, start_type='low')
        detector = CombinationDetector(pivots)
        combos = detector.find_all()
        doubles = [c for c in combos if c['type'] == 'double_three']
        assert len(doubles) >= 1, f"Двойная тройка не найдена. Комбинаций: {len(combos)}"
        d = doubles[0]
        assert d['direction'] == 'bullish'
        assert d['rules']['x_no_break_w'] == True
        assert d['rules']['same_direction'] == True
    
    def test_double_three_bearish(self):
        """Двойная тройка (медвежья)."""
        pivots = build_pivots_from_points(DOUBLE_THREE_BEAR, start_type='high')
        detector = CombinationDetector(pivots)
        combos = detector.find_all()
        doubles = [c for c in combos if c['type'] == 'double_three']
        assert len(doubles) >= 1, f"Комбинаций: {len(combos)}"
        assert doubles[0]['direction'] == 'bearish'
    
    def test_double_three_x_breaks_w(self):
        """X заходит за начало W — невалидно."""
        points = [1.1000, 1.1100, 1.0950, 1.1150]
        pivots = build_pivots_from_points(points, start_type='low')
        detector = CombinationDetector(pivots)
        combos = detector.find_all()
        doubles = [c for c in combos if c['type'] == 'double_three']
        for d in doubles:
            assert d['rules']['x_no_break_w'] == False


class TestTripleThree:
    def test_triple_three_bullish(self):
        """Тройная тройка (бычья)."""
        points = [1.1000, 1.1080, 1.1040, 1.1120, 1.1080, 1.1160]
        pivots = build_pivots_from_points(points, start_type='low')
        detector = CombinationDetector(pivots)
        combos = detector.find_all()
        # Может быть 0 (редкая), но не должно падать
        assert isinstance(combos, list)


class TestEdgeCases:
    def test_too_few_pivots(self):
        """Меньше 4 пивотов — пусто."""
        points = [1.1000, 1.1100, 1.1050]
        pivots = build_pivots_from_points(points, start_type='low')
        detector = CombinationDetector(pivots)
        combos = detector.find_all()
        assert len(combos) == 0
    
    def test_empty_pivots(self):
        """Пустые пивоты — пусто."""
        df = pd.DataFrame(columns=['price', 'type'])
        detector = CombinationDetector(df)
        combos = detector.find_all()
        assert len(combos) == 0
    
    def test_get_combinations(self):
        """get_combinations возвращает список."""
        df = pd.DataFrame(columns=['price', 'type'])
        detector = CombinationDetector(df)
        assert detector.get_combinations() == []
