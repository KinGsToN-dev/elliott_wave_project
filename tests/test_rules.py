"""
Тесты для rules.alternation, rules.extension, rules.divergence.
"""
import pytest
import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rules.alternation import AlternationChecker, DEEP_THRESHOLD, FLAT_THRESHOLD
from rules.extension import ExtensionAnalyzer, EXTENSION_RATIO
from rules.divergence import RulesDivergence


def make_impulse(w1_len, w2_len, w3_len, w4_len, w5_len, direction='bullish'):
    """Хелпер: создаёт импульс с заданными длинами волн."""
    t = datetime(2026, 1, 1)
    if direction == 'bullish':
        p0 = 1.1000
        p1 = p0 + w1_len
        p2 = p1 - w2_len
        p3 = p2 + w3_len
        p4 = p3 - w4_len
        p5 = p4 + w5_len
    else:
        p0 = 1.2000
        p1 = p0 - w1_len
        p2 = p1 + w2_len
        p3 = p2 - w3_len
        p4 = p3 + w4_len
        p5 = p4 - w5_len
    
    return {
        'direction': direction,
        'points': [
            (t, p0, '0'), (t + timedelta(hours=5), p1, '1'),
            (t + timedelta(hours=10), p2, '2'), (t + timedelta(hours=15), p3, '3'),
            (t + timedelta(hours=20), p4, '4'), (t + timedelta(hours=25), p5, '5'),
        ],
    }


# ============================================================
# ALTERNATION
# ============================================================
class TestAlternation:
    def test_classify_deep(self):
        """W2 = 61.8% — глубокая."""
        checker = AlternationChecker()
        assert checker.classify_w2(0.618) == 'deep'
    
    def test_classify_flat(self):
        """W2 = 23.6% — плоская."""
        checker = AlternationChecker()
        assert checker.classify_w2(0.236) == 'flat'
    
    def test_alternation_deep_flat(self):
        """W2 глубокая + W4 плоская = чередование OK."""
        checker = AlternationChecker()
        result = checker.check_alternation(0.618, 0.300)
        assert result['valid'] == True
        assert result['w2_type'] == 'deep'
        assert result['w4_type'] == 'flat'
    
    def test_alternation_flat_deep(self):
        """W2 плоская + W4 глубокая = чередование OK."""
        checker = AlternationChecker()
        result = checker.check_alternation(0.300, 0.618)
        assert result['valid'] == True
    
    def test_no_alternation(self):
        """W2 глубокая + W4 глубокая = НЕТ чередования."""
        checker = AlternationChecker()
        result = checker.check_alternation(0.618, 0.700)
        assert result['valid'] == False
    
    def test_diagonal_no_alternation(self):
        """В диагонали чередования нет."""
        checker = AlternationChecker()
        result = checker.check_alternation(0.618, 0.700, is_diagonal=True)
        assert result['valid'] == True
        assert result['rule'] == 'no_alternation_in_diagonal'
    
    def test_calculate_all(self):
        """calculate_all обрабатывает список импульсов."""
        checker = AlternationChecker()
        # W1=0.01, W2=0.005 (50%), W3=0.02, W4=0.005 (25%), W5=0.01
        imp = make_impulse(0.0100, 0.0050, 0.0200, 0.0050, 0.0100)
        results = checker.calculate_all([imp])
        assert len(results) == 1


# ============================================================
# EXTENSION
# ============================================================
class TestExtension:
    def test_find_w3_extension(self):
        """W3 растянута (в 2× длиннее W1 и W5)."""
        analyzer = ExtensionAnalyzer()
        result = analyzer.find_extension(0.0100, 0.0300, 0.0100)
        assert result['extension'] == 'W3'
    
    def test_no_extension(self):
        """Все волны примерно равны — нет растяжения."""
        analyzer = ExtensionAnalyzer()
        result = analyzer.find_extension(0.0100, 0.0100, 0.0100)
        assert result['extension'] is None
    
    def test_w1_extension(self):
        """W1 растянута."""
        analyzer = ExtensionAnalyzer()
        result = analyzer.find_extension(0.0300, 0.0100, 0.0100)
        assert result['extension'] == 'W1'
    
    def test_w5_extension(self):
        """W5 растянута."""
        analyzer = ExtensionAnalyzer()
        result = analyzer.find_extension(0.0100, 0.0100, 0.0300)
        assert result['extension'] == 'W5'
    
    def test_check_w3_rule(self):
        """W3 растянута — W1 и W5 пропорциональны."""
        analyzer = ExtensionAnalyzer()
        result = analyzer.check_w3_extension(0.0100, 0.0100)
        assert result['valid'] == True
    
    def test_check_w5_rule(self):
        """W5 растянута — W5 = 161.8% от W3."""
        analyzer = ExtensionAnalyzer()
        result = analyzer.check_w5_extension(0.0100, 0.01618)
        assert result['valid'] == True
    
    def test_calculate_all(self):
        """calculate_all обрабатывает список импульсов."""
        analyzer = ExtensionAnalyzer()
        imp = make_impulse(0.0100, 0.0050, 0.0300, 0.0050, 0.0100)
        results = analyzer.calculate_all([imp])
        assert len(results) == 1
        assert results[0]['extension'] == 'W3'


# ============================================================
# DIVERGENCE
# ============================================================
class TestRulesDivergence:
    def test_no_df(self):
        """Без df — дивергенция no_data."""
        div = RulesDivergence(df=None)
        imp = make_impulse(0.0100, 0.0050, 0.0200, 0.0050, 0.0100)
        results = div.calculate_all([imp])
        assert len(results) == 1
        assert results[0]['divergence']['type'] == 'no_data'
    
    def test_empty_corrections(self):
        """Только импульсы — без ошибок."""
        div = RulesDivergence(df=None)
        imp = make_impulse(0.0100, 0.0050, 0.0200, 0.0050, 0.0100)
        results = div.calculate_all([imp], [])
        assert len(results) == 1
    
    def test_get_results(self):
        """get_results возвращает список."""
        div = RulesDivergence(df=None)
        div.calculate_all([])
        assert div.get_results() == []


class TestABCAlternation:
    def test_abc_alternation_deep_flat(self):
        """A глубокая -> B плоская."""
        from rules.alternation import AlternationChecker
        checker = AlternationChecker()
        result = checker.check_abc_alternation(0.618, 0.300)
        assert result['valid'] == True
    
    def test_abc_alternation_flat_deep(self):
        """A плоская -> B глубокая."""
        from rules.alternation import AlternationChecker
        checker = AlternationChecker()
        result = checker.check_abc_alternation(0.300, 0.618)
        assert result['valid'] == True
    
    def test_abc_no_alternation(self):
        """A глубокая, B глубокая — нет чередования."""
        from rules.alternation import AlternationChecker
        checker = AlternationChecker()
        result = checker.check_abc_alternation(0.618, 0.700)
        assert result['valid'] == False
