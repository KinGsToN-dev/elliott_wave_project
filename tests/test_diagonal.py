"""
Тесты для patterns.diagonal.DiagonalDetector
"""
import pytest
import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.zigzag import ZigZag
from patterns.diagonal import DiagonalDetector
from tests.generate_test_data import (
    make_leading_contracting_bullish,
    make_ending_contracting_bullish,
    make_leading_expanding_bullish,
    make_bearish_contracting_diagonal,
)


def build_pivots_from_points(points, start_type='low'):
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


# Правильные точки для диагоналей
LEADING_CONTRACTING = [1.1000, 1.1100, 1.1040, 1.1120, 1.1070, 1.1100]
ENDING_CONTRACTING  = [1.1000, 1.1120, 1.1060, 1.1150, 1.1095, 1.1130]
LEADING_EXPANDING   = [1.1000, 1.1040, 1.1020, 1.1090, 1.1030, 1.1120]
BEARISH_CONTRACTING = [1.2000, 1.1900, 1.1960, 1.1880, 1.1930, 1.1900]


class TestContractingDiagonal:
    def test_leading_contracting_bullish(self):
        pivots = build_pivots_from_points(LEADING_CONTRACTING, start_type='low')
        detector = DiagonalDetector(pivots)
        diagonals = detector.find_diagonals()
        assert len(diagonals) >= 1, "Диагональ не найдена"
        d = diagonals[0]
        assert d['direction'] == 'bullish'
        assert d['shape'] == 'contracting'
        assert d['rules']['w4_overlaps_w1'] == True
    
    def test_ending_contracting_bullish(self):
        pivots = build_pivots_from_points(ENDING_CONTRACTING, start_type='low')
        detector = DiagonalDetector(pivots)
        diagonals = detector.find_diagonals()
        assert len(diagonals) >= 1
        assert diagonals[0]['shape'] == 'contracting'


class TestExpandingDiagonal:
    def test_leading_expanding_bullish(self):
        pivots = build_pivots_from_points(LEADING_EXPANDING, start_type='low')
        detector = DiagonalDetector(pivots)
        diagonals = detector.find_diagonals()
        assert len(diagonals) >= 1
        assert diagonals[0]['shape'] == 'expanding'


class TestBearishDiagonal:
    def test_bearish_contracting(self):
        pivots = build_pivots_from_points(BEARISH_CONTRACTING, start_type='high')
        detector = DiagonalDetector(pivots)
        diagonals = detector.find_diagonals()
        assert len(diagonals) >= 1
        assert diagonals[0]['direction'] == 'bearish'


class TestRules:
    def test_w2_no_break_w1(self):
        pivots = build_pivots_from_points(LEADING_CONTRACTING, start_type='low')
        detector = DiagonalDetector(pivots)
        diagonals = detector.find_diagonals()
        assert diagonals[0]['rules']['w2_no_break_w1'] == True
    
    def test_w3_breaks_w1(self):
        pivots = build_pivots_from_points(LEADING_CONTRACTING, start_type='low')
        detector = DiagonalDetector(pivots)
        diagonals = detector.find_diagonals()
        assert diagonals[0]['rules']['w3_breaks_w1'] == True
    
    def test_w4_overlaps_w1(self):
        pivots = build_pivots_from_points(LEADING_CONTRACTING, start_type='low')
        detector = DiagonalDetector(pivots)
        diagonals = detector.find_diagonals()
        assert diagonals[0]['rules']['w4_overlaps_w1'] == True
    
    def test_w4_no_break_w2(self):
        pivots = build_pivots_from_points(LEADING_CONTRACTING, start_type='low')
        detector = DiagonalDetector(pivots)
        diagonals = detector.find_diagonals()
        assert diagonals[0]['rules']['w4_no_break_w2'] == True


class TestShapeClassification:
    def test_contracting_lengths(self):
        pivots = build_pivots_from_points(LEADING_CONTRACTING, start_type='low')
        detector = DiagonalDetector(pivots)
        diagonals = detector.find_diagonals()
        d = diagonals[0]
        assert d['w1'] > d['w3'] > d['w5']
        assert d['w2'] > d['w4']
    
    def test_expanding_lengths(self):
        pivots = build_pivots_from_points(LEADING_EXPANDING, start_type='low')
        detector = DiagonalDetector(pivots)
        diagonals = detector.find_diagonals()
        d = diagonals[0]
        assert d['w1'] < d['w3'] < d['w5']
        assert d['w2'] < d['w4']


class TestNegativeCases:
    def test_no_diagonal_on_impulse(self):
        points = [1.1000, 1.1100, 1.1050, 1.1300, 1.1200, 1.1450]
        pivots = build_pivots_from_points(points, start_type='low')
        detector = DiagonalDetector(pivots)
        diagonals = detector.find_diagonals()
        for d in diagonals:
            assert d['rules']['w4_overlaps_w1'] == True
    
    def test_empty_pivots(self):
        df = pd.DataFrame(columns=['price', 'type'])
        detector = DiagonalDetector(df)
        diagonals = detector.find_diagonals()
        assert len(diagonals) == 0


class TestIntegration:
    def test_full_pipeline_leading(self):
        df = make_leading_contracting_bullish()
        zz = ZigZag(df, length=2)
        pivots = zz.find_pivots()
        detector = DiagonalDetector(pivots, df=None, min_atr_ratio=0.1)
        diagonals = detector.find_diagonals()
        assert len(diagonals) >= 1, f"Диагональ не найдена. Пивотов: {len(pivots)}"
    
    def test_full_pipeline_ending(self):
        df = make_ending_contracting_bullish()
        zz = ZigZag(df, length=2)
        pivots = zz.find_pivots()
        detector = DiagonalDetector(pivots, df=None, min_atr_ratio=0.1)
        diagonals = detector.find_diagonals()
        assert len(diagonals) >= 1
    
    def test_full_pipeline_expanding(self):
        df = make_leading_expanding_bullish()
        zz = ZigZag(df, length=2)
        pivots = zz.find_pivots()
        detector = DiagonalDetector(pivots, df=None, min_atr_ratio=0.1)
        diagonals = detector.find_diagonals()
        assert len(diagonals) >= 1


class TestThrowOver:
    def test_throw_over_contracting(self):
        """Выброс в сужающейся диагонали."""
        import pandas as pd
        from patterns.diagonal import DiagonalDetector
        detector = DiagonalDetector(pd.DataFrame())
        result = detector.check_throw_over(1.1100, 1.1140, 1.1200, 'contracting')
        assert 'is_throw_over' in result
        assert 'expected_w5' in result
    
    def test_shortfall_expanding(self):
        """Недобой в расширяющейся диагонали."""
        import pandas as pd
        from patterns.diagonal import DiagonalDetector
        detector = DiagonalDetector(pd.DataFrame())
        result = detector.check_throw_over(1.1100, 1.1140, 1.1100, 'expanding')
        assert 'is_shortfall' in result
    
    def test_no_throw_over(self):
        """Без выброса."""
        import pandas as pd
        from patterns.diagonal import DiagonalDetector
        detector = DiagonalDetector(pd.DataFrame())
        result = detector.check_throw_over(1.1100, 1.1140, 1.1180, 'contracting')
        assert isinstance(result['is_throw_over'], bool)
