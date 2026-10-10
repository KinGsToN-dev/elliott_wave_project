"""
Тесты для patterns.impulse.ImpulseDetector
"""
import pytest
import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.zigzag import ZigZag
from patterns.impulse import ImpulseDetector


def build_pivots_from_points(points, start_type='low', start_time=None):
    if start_time is None:
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


class TestBullishImpulse:
    def test_valid_bullish(self):
        points = [1.1000, 1.1100, 1.1050, 1.1300, 1.1200, 1.1450]
        pivots = build_pivots_from_points(points, start_type='low')
        detector = ImpulseDetector(pivots)
        impulses = detector.find_impulses()
        assert len(impulses) == 1
        assert impulses[0]['direction'] == 'bullish'
    
    def test_bullish_rules_all_pass(self):
        points = [1.1000, 1.1100, 1.1050, 1.1300, 1.1200, 1.1450]
        pivots = build_pivots_from_points(points, start_type='low')
        detector = ImpulseDetector(pivots)
        impulses = detector.find_impulses()
        rules = impulses[0]['rules']
        assert rules['w2_no_break_w1'] == True
        assert rules['w3_breaks_w1'] == True
        assert rules['w4_no_overlap_w1'] == True
        assert rules['w3_not_shortest'] == True


class TestBearishImpulse:
    def test_valid_bearish(self):
        points = [1.2000, 1.1900, 1.1950, 1.1700, 1.1800, 1.1550]
        pivots = build_pivots_from_points(points, start_type='high')
        detector = ImpulseDetector(pivots)
        impulses = detector.find_impulses()
        assert len(impulses) == 1
        assert impulses[0]['direction'] == 'bearish'


class TestInvalidImpulses:
    def test_w2_breaks_w1(self):
        points = [1.1000, 1.1100, 1.0950, 1.1300, 1.1200, 1.1400]
        pivots = build_pivots_from_points(points, start_type='low')
        detector = ImpulseDetector(pivots)
        impulses = detector.find_impulses()
        assert len(impulses) == 0
    
    def test_w3_shortest(self):
        points = [1.1000, 1.1100, 1.1050, 1.1080, 1.1050, 1.1200]
        pivots = build_pivots_from_points(points, start_type='low')
        detector = ImpulseDetector(pivots)
        impulses = detector.find_impulses()
        assert len(impulses) == 0
    
    def test_w4_overlaps_w1(self):
        points = [1.1000, 1.1100, 1.1050, 1.1300, 1.1080, 1.1400]
        pivots = build_pivots_from_points(points, start_type='low')
        detector = ImpulseDetector(pivots)
        impulses = detector.find_impulses()
        assert len(impulses) == 0


class TestExtension:
    def test_extension_w3(self):
        points = [1.1000, 1.1100, 1.1050, 1.1400, 1.1200, 1.1350]
        pivots = build_pivots_from_points(points, start_type='low')
        detector = ImpulseDetector(pivots)
        impulses = detector.find_impulses()
        assert len(impulses) == 1
        assert impulses[0]['extension'] == 'W3'
    
    def test_no_extension(self):
        """Все волны примерно равны — нет растяжения."""
        # W1, W3, W5 почти одинаковые (все ~0.008-0.009)
        points = [1.1000, 1.1080, 1.1040, 1.1120, 1.1085, 1.1165]
        pivots = build_pivots_from_points(points, start_type='low')
        detector = ImpulseDetector(pivots)
        impulses = detector.find_impulses()
        assert len(impulses) == 1, f"Пивотов: {len(pivots)}, импульсов: {len(impulses)}"
        assert impulses[0]['extension'] is None


class TestTruncated:
    def test_truncated_5th(self):
        points = [1.1000, 1.1100, 1.1050, 1.1300, 1.1200, 1.1280]
        pivots = build_pivots_from_points(points, start_type='low')
        detector = ImpulseDetector(pivots)
        impulses = detector.find_impulses()
        assert len(impulses) == 1
        assert impulses[0]['truncated'] == True
    
    def test_not_truncated(self):
        points = [1.1000, 1.1100, 1.1050, 1.1300, 1.1200, 1.1450]
        pivots = build_pivots_from_points(points, start_type='low')
        detector = ImpulseDetector(pivots)
        impulses = detector.find_impulses()
        assert len(impulses) == 1
        assert impulses[0]['truncated'] == False


class TestEdgeCases:
    def test_too_few_pivots(self):
        points = [1.1000, 1.1100, 1.1050]
        pivots = build_pivots_from_points(points, start_type='low')
        detector = ImpulseDetector(pivots)
        impulses = detector.find_impulses()
        assert len(impulses) == 0
    
    def test_empty_pivots(self):
        df = pd.DataFrame(columns=['price', 'type'])
        detector = ImpulseDetector(df)
        impulses = detector.find_impulses()
        assert len(impulses) == 0


class TestDoublePattern:
    def test_double_top_bullish(self):
        """Усечённый бычий импульс -> двойная вершина."""
        import pandas as pd
        from patterns.impulse import ImpulseDetector
        detector = ImpulseDetector(pd.DataFrame())
        imp = {'truncated': True, 'direction': 'bullish'}
        result = detector.detect_double_pattern(imp)
        assert result['pattern'] == 'double_top'
    
    def test_double_bottom_bearish(self):
        """Усечённый медвежий импульс -> двойное дно."""
        import pandas as pd
        from patterns.impulse import ImpulseDetector
        detector = ImpulseDetector(pd.DataFrame())
        imp = {'truncated': True, 'direction': 'bearish'}
        result = detector.detect_double_pattern(imp)
        assert result['pattern'] == 'double_bottom'
    
    def test_no_truncation(self):
        """Без усечения -> нет паттерна."""
        import pandas as pd
        from patterns.impulse import ImpulseDetector
        detector = ImpulseDetector(pd.DataFrame())
        imp = {'truncated': False, 'direction': 'bullish'}
        result = detector.detect_double_pattern(imp)
        assert result is None
