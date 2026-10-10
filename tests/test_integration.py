"""
Интеграционные тесты: полный цикл от данных до импульсов.
"""
import pytest
import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.zigzag import ZigZag
from patterns.impulse import ImpulseDetector
from tests.generate_test_data import (
    make_bullish_impulse, make_bearish_impulse,
    make_invalid_w2_breaks_w1, make_truncated_5th
)


class TestFullPipeline:
    def test_bullish_pipeline(self):
        df = make_bullish_impulse()
        zz = ZigZag(df, length=2)
        pivots = zz.find_pivots()
        detector = ImpulseDetector(pivots, df=None, min_atr_ratio=0.1)
        impulses = detector.find_impulses()
        assert len(impulses) >= 1, f"Бычий импульс не найден. Пивотов: {len(pivots)}"
        assert impulses[0]['direction'] == 'bullish'
    
    def test_bearish_pipeline(self):
        df = make_bearish_impulse()
        zz = ZigZag(df, length=2)
        pivots = zz.find_pivots()
        detector = ImpulseDetector(pivots, df=None, min_atr_ratio=0.1)
        impulses = detector.find_impulses()
        assert len(impulses) >= 1, f"Медвежий импульс не найден. Пивотов: {len(pivots)}"
        assert impulses[0]['direction'] == 'bearish'
    
    def test_invalid_w2_pipeline(self):
        df = make_invalid_w2_breaks_w1()
        zz = ZigZag(df, length=2)
        pivots = zz.find_pivots()
        detector = ImpulseDetector(pivots, df=None, min_atr_ratio=0.1)
        impulses = detector.find_impulses()
        for imp in impulses:
            assert imp['rules']['w2_no_break_w1'] == True
    
    def test_truncated_pipeline(self):
        df = make_truncated_5th()
        zz = ZigZag(df, length=2)
        pivots = zz.find_pivots()
        detector = ImpulseDetector(pivots, df=None, min_atr_ratio=0.1)
        impulses = detector.find_impulses()
        assert isinstance(impulses, list)
    
    def test_no_data(self):
        df = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'tick_volume'])
        zz = ZigZag(df, length=2)
        pivots = zz.find_pivots()
        detector = ImpulseDetector(pivots)
        impulses = detector.find_impulses()
        assert len(impulses) == 0
