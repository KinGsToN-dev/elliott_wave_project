"""
Тесты для patterns.correction.CorrectionDetector
"""
import pytest
import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.zigzag import ZigZag
from patterns.correction import CorrectionDetector


def build_pivots_from_points(points, start_type='high'):
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
ZIGZAG_CORR   = [1.1500, 1.1400, 1.1450, 1.1300]
FLAT_REGULAR  = [1.1500, 1.1450, 1.1500, 1.1400]
FLAT_EXPANDED = [1.1500, 1.1450, 1.1550, 1.1350]
FLAT_RUNNING  = [1.1500, 1.1450, 1.1550, 1.1460]

# Треугольники (start_type='low')
# Симметричный: A=0.01, B=0.008, C=0.006, D=0.005, E=0.004
TRIANGLE_SYMMETRIC = [1.1500, 1.1600, 1.1520, 1.1580, 1.1530, 1.1570]
# Восходящий: D на уровне B, E > C
TRIANGLE_ASCENDING = [1.1500, 1.1600, 1.1500, 1.1570, 1.1500, 1.1600]
# Расширяющийся: A=0.002, B=0.004, C=0.008, D=0.012, E=0.021
TRIANGLE_EXPANDING = [1.1500, 1.1520, 1.1480, 1.1560, 1.1440, 1.1650]


class TestZigzag:
    def test_zigzag_correction(self):
        pivots = build_pivots_from_points(ZIGZAG_CORR, start_type='high')
        detector = CorrectionDetector(pivots)
        corrections = detector.find_corrections()
        zigzags = [c for c in corrections if c['type'] == 'zigzag']
        assert len(zigzags) >= 1, f"Зигзаг не найден. Коррекций: {len(corrections)}"
        z = zigzags[0]
        assert z['rules']['w_b_no_break_w_a'] == True
        assert z['rules']['w_c_lower_than_a'] == True


class TestFlat:
    def test_flat_regular(self):
        pivots = build_pivots_from_points(FLAT_REGULAR, start_type='high')
        detector = CorrectionDetector(pivots)
        corrections = detector.find_corrections()
        flats = [c for c in corrections if c['type'] == 'flat']
        assert len(flats) >= 1, f"Плоскость не найдена. Коррекций: {len(corrections)}"
    
    def test_flat_expanded(self):
        pivots = build_pivots_from_points(FLAT_EXPANDED, start_type='high')
        detector = CorrectionDetector(pivots)
        corrections = detector.find_corrections()
        flats = [c for c in corrections if c['type'] == 'flat']
        assert len(flats) >= 1, "Расширенная плоскость не найдена"
    
    def test_flat_running(self):
        pivots = build_pivots_from_points(FLAT_RUNNING, start_type='high')
        detector = CorrectionDetector(pivots)
        corrections = detector.find_corrections()
        flats = [c for c in corrections if c['type'] == 'flat']
        assert len(flats) >= 1, "Бегущая плоскость не найдена"


class TestTriangle:
    def test_triangle_symmetric(self):
        """Симметричный: каждая волна меньше предыдущей."""
        pivots = build_pivots_from_points(TRIANGLE_SYMMETRIC, start_type='low')
        detector = CorrectionDetector(pivots)
        corrections = detector.find_corrections()
        triangles = [c for c in corrections if c['type'] == 'triangle']
        assert len(triangles) >= 1, f"Симметричный треугольник не найден. Коррекций: {len(corrections)}"
        assert triangles[0]['subtype'] == 'symmetric'
    
    def test_triangle_ascending(self):
        """Восходящий: D на уровне B, E > C."""
        pivots = build_pivots_from_points(TRIANGLE_ASCENDING, start_type='low')
        detector = CorrectionDetector(pivots)
        corrections = detector.find_corrections()
        triangles = [c for c in corrections if c['type'] == 'triangle']
        assert len(triangles) >= 1, f"Восходящий треугольник не найден. Коррекций: {len(corrections)}"
    
    def test_triangle_expanding(self):
        """Расширяющийся: каждая волна больше предыдущей."""
        pivots = build_pivots_from_points(TRIANGLE_EXPANDING, start_type='low')
        detector = CorrectionDetector(pivots)
        corrections = detector.find_corrections()
        triangles = [c for c in corrections if c['type'] == 'triangle']
        assert len(triangles) >= 1, f"Расширяющийся треугольник не найден. Коррекций: {len(corrections)}"
        assert triangles[0]['subtype'] == 'expanding'


class TestEdgeCases:
    def test_too_few_pivots(self):
        points = [1.1500, 1.1400]
        pivots = build_pivots_from_points(points, start_type='high')
        detector = CorrectionDetector(pivots)
        corrections = detector.find_corrections()
        assert len(corrections) == 0
    
    def test_empty_pivots(self):
        df = pd.DataFrame(columns=['price', 'type'])
        detector = CorrectionDetector(df)
        corrections = detector.find_corrections()
        assert len(corrections) == 0
