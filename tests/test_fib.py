"""
Тесты для fib.retracement, fib.extension, fib.orthodox, fib.clusters.
"""
import pytest
import sys
import os
import numpy as np
import pandas as pd
import pandas as pd
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fib.retracement import RetracementCalculator, DEEP_LEVELS, FLAT_LEVELS, W4_LEVELS
from fib.extension import ExtensionCalculator, W3_LEVELS, W5_LEVELS, WC_ZIGZAG_LEVELS
from fib.orthodox import OrthodoxPointsDetector
from fib.clusters import ClusterFinder


# ============================================================
# RETRACEMENT (существующие)
# ============================================================
class TestRetracementW2:
    def test_w2_deep_levels(self):
        calc = RetracementCalculator()
        result = calc.calculate_w2_levels(1.1000, 1.1100, 'deep')
        assert result['wave'] == 'W2'
        assert result['type'] == 'deep'
        assert len(result['levels']) == 3
        assert 0.500 in result['levels']
        assert 0.618 in result['levels']
        assert 0.786 in result['levels']
    
    def test_w2_deep_values(self):
        calc = RetracementCalculator()
        result = calc.calculate_w2_levels(1.1000, 1.1100, 'deep')
        assert abs(result['levels'][0.500] - 1.1050) < 0.0001
        assert abs(result['levels'][0.618] - 1.10382) < 0.0001
    
    def test_w2_flat_levels(self):
        calc = RetracementCalculator()
        result = calc.calculate_w2_levels(1.1000, 1.1100, 'flat')
        assert result['type'] == 'flat'
        assert 0.236 in result['levels']
        assert 0.382 in result['levels']
        assert 0.500 in result['levels']


class TestRetracementW4:
    def test_w4_levels(self):
        calc = RetracementCalculator()
        result = calc.calculate_w4_levels(1.1100, 1.1300)
        assert result['wave'] == 'W4'
        assert 0.382 in result['levels']
        assert 0.500 in result['levels']
    
    def test_w4_values(self):
        calc = RetracementCalculator()
        result = calc.calculate_w4_levels(1.1100, 1.1300)
        assert abs(result['levels'][0.382] - 1.12236) < 0.0001
        assert abs(result['levels'][0.500] - 1.1200) < 0.0001


class TestRetracementWB:
    def test_wb_zigzag(self):
        calc = RetracementCalculator()
        result = calc.calculate_wb_levels(1.1500, 1.1400, 'zigzag')
        assert result['wave'] == 'W_B'
        assert 0.500 in result['levels']
        assert 0.618 in result['levels']
        assert 0.900 in result['levels']
    
    def test_wb_flat(self):
        calc = RetracementCalculator()
        result = calc.calculate_wb_levels(1.1500, 1.1400, 'flat')
        assert result['type'] == 'flat'
        assert 0.900 in result['levels']
        assert 1.000 in result['levels']
        assert 1.236 in result['levels']


class TestFullCalculation:
    def test_calculate_all_with_impulse(self):
        calc = RetracementCalculator()
        impulse = {
            'points': [
                (None, 1.1000, '0'), (None, 1.1100, '1'),
                (None, 1.1050, '2'), (None, 1.1300, '3'),
                (None, 1.1200, '4'), (None, 1.1450, '5'),
            ],
            'direction': 'bullish',
        }
        results = calc.calculate_all([impulse], [])
        assert len(results) == 1
        assert 'w2' in results[0]
        assert 'w4' in results[0]
    
    def test_calculate_all_with_zigzag(self):
        calc = RetracementCalculator()
        corr = {
            'type': 'zigzag', 'direction': 'bearish',
            'points': [
                (None, 1.1500, '0'), (None, 1.1400, 'A'),
                (None, 1.1450, 'B'), (None, 1.1300, 'C'),
            ],
        }
        results = calc.calculate_all([], [corr])
        assert len(results) == 1
        assert 'wb' in results[0]
    
    def test_calculate_all_with_flat(self):
        calc = RetracementCalculator()
        corr = {
            'type': 'flat', 'direction': 'bearish', 'subtype': 'regular',
            'points': [
                (None, 1.1500, '0'), (None, 1.1450, 'A'),
                (None, 1.1500, 'B'), (None, 1.1400, 'C'),
            ],
        }
        results = calc.calculate_all([], [corr])
        assert len(results) == 1
        assert 'wb' in results[0]
        assert results[0]['wb']['type'] == 'flat'
    
    def test_get_last_results(self):
        calc = RetracementCalculator()
        calc.calculate_all([], [])
        assert calc.get_last_results() == []


# ============================================================
# EXTENSION
# ============================================================
class TestExtensionW3:
    def test_w3_levels(self):
        calc = ExtensionCalculator()
        result = calc.calculate_w3_targets(1.1000, 1.1100, 1.1050)
        assert result['wave'] == 'W3'
        assert 1.618 in result['targets']
        assert 2.000 in result['targets']
        assert 2.618 in result['targets']
    
    def test_w3_161_value(self):
        calc = ExtensionCalculator()
        result = calc.calculate_w3_targets(1.1000, 1.1100, 1.1050)
        assert abs(result['targets'][1.618] - 1.12118) < 0.0001


class TestExtensionW5:
    def test_w5_levels(self):
        calc = ExtensionCalculator()
        result = calc.calculate_w5_targets(1.1000, 1.1250, 1.1150)
        assert result['wave'] == 'W5'
        assert 0.618 in result['targets']
        assert 1.000 in result['targets']
        assert 1.618 in result['targets']
    
    def test_w5_100_value(self):
        calc = ExtensionCalculator()
        result = calc.calculate_w5_targets(1.1000, 1.1250, 1.1150)
        assert abs(result['targets'][1.000] - 1.1400) < 0.0001


class TestExtensionWC:
    def test_wc_zigzag(self):
        calc = ExtensionCalculator()
        result = calc.calculate_wc_targets(1.1500, 1.1400, 'zigzag')
        assert result['wave'] == 'W_C'
        assert 0.618 in result['targets']
        assert 1.000 in result['targets']
        assert 1.272 in result['targets']
        assert 1.618 in result['targets']
    
    def test_wc_flat_expanded(self):
        calc = ExtensionCalculator()
        result = calc.calculate_wc_targets(1.1500, 1.1400, 'flat_expanded')
        assert 1.618 in result['targets']
        assert len(result['targets']) == 1
    
    def test_wc_flat_running(self):
        calc = ExtensionCalculator()
        result = calc.calculate_wc_targets(1.1500, 1.1400, 'flat_running')
        assert 1.000 in result['targets']
        assert len(result['targets']) == 1


class TestExtensionFull:
    def test_calculate_all_impulse(self):
        calc = ExtensionCalculator()
        impulse = {
            'points': [
                (None, 1.1000, '0'), (None, 1.1100, '1'),
                (None, 1.1050, '2'), (None, 1.1300, '3'),
                (None, 1.1200, '4'), (None, 1.1450, '5'),
            ],
            'direction': 'bullish',
        }
        results = calc.calculate_all([impulse], [])
        assert len(results) == 1
        assert 'w3' in results[0]
        assert 'w5' in results[0]
    
    def test_get_last_results(self):
        calc = ExtensionCalculator()
        calc.calculate_all([], [])
        assert calc.get_last_results() == []


# ============================================================
# ORTHODOX POINTS
# ============================================================
class TestOrthodoxPoints:
    def test_orthodox_regular(self):
        """Обычный паттерн — ортодоксальная точка = последняя."""
        detector = OrthodoxPointsDetector()
        pattern = {
            'points': [
                (datetime(2026, 1, 1), 1.1000, '0'),
                (datetime(2026, 1, 2), 1.1100, '1'),
                (datetime(2026, 1, 3), 1.1050, '2'),
                (datetime(2026, 1, 4), 1.1300, '3'),
                (datetime(2026, 1, 5), 1.1200, '4'),
                (datetime(2026, 1, 6), 1.1450, '5'),
            ],
            'truncated': False,
        }
        time, price = detector.get_orthodox_end(pattern)
        assert price == 1.1450
    
    def test_orthodox_truncated(self):
        """Усечённый импульс — ортодоксальная точка = W3."""
        detector = OrthodoxPointsDetector()
        pattern = {
            'points': [
                (datetime(2026, 1, 1), 1.1000, '0'),
                (datetime(2026, 1, 2), 1.1100, '1'),
                (datetime(2026, 1, 3), 1.1050, '2'),
                (datetime(2026, 1, 4), 1.1300, '3'),
                (datetime(2026, 1, 5), 1.1200, '4'),
                (datetime(2026, 1, 6), 1.1280, '5'),  # ниже W3
            ],
            'truncated': True,
        }
        time, price = detector.get_orthodox_end(pattern)
        assert price == 1.1300, "Ортодоксальная точка должна быть в W3"
    
    def test_adjust_pattern(self):
        """adjust_pattern добавляет orthodox_start/end."""
        detector = OrthodoxPointsDetector()
        pattern = {
            'points': [
                (datetime(2026, 1, 1), 1.1000, '0'),
                (datetime(2026, 1, 2), 1.1450, '5'),
            ],
            'truncated': False,
        }
        adj = detector.adjust_pattern(pattern)
        assert 'orthodox_start' in adj
        assert 'orthodox_end' in adj
        assert adj['orthodox_end'][1] == 1.1450
    
    def test_find_all(self):
        """find_all обрабатывает список паттернов."""
        detector = OrthodoxPointsDetector()
        patterns = [
            {'points': [(None, 1.1000, '0'), (None, 1.1100, '5')], 'truncated': False},
            {'points': [(None, 1.2000, '0'), (None, 1.2100, '5')], 'truncated': False},
        ]
        adjusted = detector.find_all_orthodox(patterns)
        assert len(adjusted) == 2
        assert len(detector.get_points()) == 2


# ============================================================
# CLUSTERS
# ============================================================
class TestClusterFinder:
    def test_no_levels(self):
        """Пустой ввод — нет кластеров."""
        finder = ClusterFinder()
        clusters = finder.find_clusters([])
        assert len(clusters) == 0
    
    def test_single_level(self):
        """Один уровень — нет кластера."""
        finder = ClusterFinder()
        fib_results = [{
            'wave': 'W2', 'levels': {0.618: 1.1050},
        }]
        clusters = finder.find_clusters(fib_results)
        assert len(clusters) == 0
    
    def test_two_close_levels(self):
        """Два близких уровня — образуют кластер."""
        finder = ClusterFinder(tolerance_pct=0.005)
        fib_results = [
            {'wave': 'W2', 'levels': {0.618: 1.1050}},
            {'wave': 'W4', 'levels': {0.500: 1.1051}},
        ]
        clusters = finder.find_clusters(fib_results)
        assert len(clusters) == 1
        assert clusters[0]['strength'] == 2
    
    def test_three_levels_cluster(self):
        """Три близких уровня — сильный кластер."""
        finder = ClusterFinder(tolerance_pct=0.005)
        fib_results = [
            {'wave': 'W2', 'levels': {0.618: 1.1050}},
            {'wave': 'W4', 'levels': {0.500: 1.1051}},
            {'wave': 'W3', 'targets': {1.618: 1.1052}},
        ]
        clusters = finder.find_clusters(fib_results)
        assert len(clusters) == 1
        assert clusters[0]['strength'] == 3
    
    def test_separate_clusters(self):
        """Два отдельных кластера."""
        finder = ClusterFinder(tolerance_pct=0.001)
        fib_results = [
            {'wave': 'W2', 'levels': {0.618: 1.1050, 0.500: 1.1150}},
            {'wave': 'W4', 'levels': {0.382: 1.1051, 0.500: 1.1151}},
        ]
        clusters = finder.find_clusters(fib_results)
        assert len(clusters) == 2
    
    def test_get_strong_clusters(self):
        """Фильтр по силе кластера."""
        finder = ClusterFinder(tolerance_pct=0.005)
        fib_results = [
            {'wave': 'W2', 'levels': {0.618: 1.1050}},
            {'wave': 'W4', 'levels': {0.500: 1.1051}},
            {'wave': 'W3', 'targets': {1.618: 1.1052}},
            {'wave': 'W5', 'targets': {0.618: 1.2000}},  # одиночный
        ]
        finder.find_clusters(fib_results)
        strong = finder.get_strong_clusters(min_strength=3)
        assert len(strong) == 1
        assert strong[0]['strength'] == 3

# ============================================================
# PROPERTIES (пропорциональность)
# ============================================================
from fib.proportions import ProportionsCalculator
from fib.divergence import DivergenceDetector
from rules.extension import ExtensionAnalyzer

class TestProportionsW1W3:
    def test_w3_equals_w1(self):
        """W3 = W1 (эквивалентны) — пропорционально."""
        calc = ProportionsCalculator()
        result = calc.check_w1_w3(0.0100, 0.0100)
        assert result['ratio'] == 1.0
        assert result['proportional'] == True
    
    def test_w3_161_w1(self):
        """W3 = 161.8% от W1 — пропорционально."""
        calc = ProportionsCalculator()
        result = calc.check_w1_w3(0.0100, 0.01618)
        assert abs(result['ratio'] - 1.618) < 0.01
        assert result['proportional'] == True
    
    def test_w3_random(self):
        """W3 = 1.42 × W1 — НЕ пропорционально."""
        calc = ProportionsCalculator()
        result = calc.check_w1_w3(0.0100, 0.0142)
        assert result['proportional'] == False


class TestProportionsW1W5:
    def test_w5_100_w1(self):
        """W5 = 100% от W1 — пропорционально."""
        calc = ProportionsCalculator()
        result = calc.check_w1_w5(0.0100, 0.0100)
        assert result['proportional'] == True
    
    def test_w5_0618_w1(self):
        """W5 = 61.8% от W1 — пропорционально."""
        calc = ProportionsCalculator()
        result = calc.check_w1_w5(0.0100, 0.00618)
        assert result['proportional'] == True


class TestProportionsW4W2:
    def test_w4_100_w2(self):
        """W4 = 100% от W2 — пропорционально."""
        calc = ProportionsCalculator()
        result = calc.check_w4_vs_w2(0.0050, 0.0050)
        assert result['proportional'] == True
    
    def test_w4_161_w2(self):
        """W4 = 161.8% от W2 — пропорционально."""
        calc = ProportionsCalculator()
        result = calc.check_w4_vs_w2(0.0050, 0.00809)
        assert result['proportional'] == True


class TestProportionsAC:
    def test_ac_equal(self):
        """A = C — эквивалентны."""
        calc = ProportionsCalculator()
        result = calc.check_a_c(0.0100, 0.0100)
        assert result['equivalent'] == True
    
    def test_ac_different(self):
        """A ≠ C (1.4×) — не эквивалентны."""
        calc = ProportionsCalculator()
        result = calc.check_a_c(0.0100, 0.0140)
        assert result['equivalent'] == False


class TestProportionsAll:
    def test_calculate_all(self):
        """Полный расчёт пропорций."""
        calc = ProportionsCalculator()
        impulse = {
            'points': [
                (None, 1.1000, '0'), (None, 1.1100, '1'),
                (None, 1.1050, '2'), (None, 1.1300, '3'),
                (None, 1.1200, '4'), (None, 1.1450, '5'),
            ],
            'direction': 'bullish',
        }
        corr = {
            'type': 'zigzag', 'direction': 'bearish',
            'points': [
                (None, 1.1500, '0'), (None, 1.1400, 'A'),
                (None, 1.1450, 'B'), (None, 1.1300, 'C'),
            ],
        }
        results = calc.calculate_all([impulse], [corr])
        assert len(results) == 2
        assert results[0]['type'] == 'impulse'
        assert results[1]['type'] == 'zigzag'


# ============================================================
# DIVERGENCE
# ============================================================
class TestDivergenceWithData:
    """Тесты дивергенции с реальными данными."""
    
    def make_macd_df(self):
        """Создаёт DataFrame с реалистичными свечами."""
        import numpy as np
        np.random.seed(42)
        n = 100
        dates = [datetime(2026, 1, 1) + timedelta(hours=i) for i in range(n)]
        # Импульс вверх
        prices = [1.1000 + i * 0.0005 + np.random.randn() * 0.0002 for i in range(n)]
        df = pd.DataFrame({
            'open': prices,
            'high': [p + 0.0003 for p in prices],
            'low': [p - 0.0003 for p in prices],
            'close': prices,
            'tick_volume': [100] * n,
        }, index=dates)
        return df
    
    def test_macd_calculation(self):
        """MACD рассчитывается."""
        df = self.make_macd_df()
        detector = DivergenceDetector(df=df)
        assert detector.macd is not None
        assert 'macd' in detector.macd
        assert 'signal' in detector.macd
        assert 'histogram' in detector.macd
    
    def test_get_macd_value(self):
        """get_macd_value_at возвращает значение."""
        df = self.make_macd_df()
        detector = DivergenceDetector(df=df)
        t = df.index[50]
        val = detector.get_macd_value_at(t)
        assert val is not None
        assert isinstance(val, float)
    
    def test_get_macd_invalid_time(self):
        """Невалидное время — None."""
        df = self.make_macd_df()
        detector = DivergenceDetector(df=df)
        val = detector.get_macd_value_at(datetime(2050, 1, 1))
        assert val is None
    
    def test_check_divergence_no_data(self):
        """check_divergence без df — no_data."""
        detector = DivergenceDetector(df=None)
        result = detector.check_divergence(
            datetime(2026, 1, 1), 1.1000,
            datetime(2026, 1, 5), 1.1100,
        )
        assert result['divergence'] == False
        assert result['type'] == 'no_data'
    
    def test_check_w3_w5_divergence(self):
        """Проверка дивергенции W3/W5."""
        df = self.make_macd_df()
        detector = DivergenceDetector(df=df)
        impulse = {
            'points': [
                (df.index[10], 1.1000, '0'),
                (df.index[20], 1.1050, '1'),
                (df.index[30], 1.1030, '2'),
                (df.index[40], 1.1100, '3'),
                (df.index[50], 1.1070, '4'),
                (df.index[60], 1.1150, '5'),
            ],
        }
        result = detector.check_w3_w5_divergence(impulse)
        assert 'divergence' in result
    
    def test_check_w3_w5_invalid(self):
        """Меньше 6 точек — invalid."""
        df = self.make_macd_df()
        detector = DivergenceDetector(df=df)
        impulse = {
            'points': [
                (df.index[10], 1.1000, '0'),
                (df.index[20], 1.1050, '1'),
            ],
        }
        result = detector.check_w3_w5_divergence(impulse)
        assert result['type'] == 'invalid'
    
    def test_calculate_all_with_divergence(self):
        """calculate_all находит дивергенции."""
        df = self.make_macd_df()
        detector = DivergenceDetector(df=df)
        impulse = {
            'direction': 'bullish',
            'points': [
                (df.index[10], 1.1000, '0'),
                (df.index[20], 1.1050, '1'),
                (df.index[30], 1.1030, '2'),
                (df.index[40], 1.1100, '3'),
                (df.index[50], 1.1070, '4'),
                (df.index[60], 1.1150, '5'),
            ],
        }
        results = detector.calculate_all([impulse])
        assert isinstance(results, list)


class TestProportionsExtra:
    """Дополнительные тесты пропорций."""
    
    def test_check_w_y(self):
        """Эквивалентность W и Y."""
        calc = ProportionsCalculator()
        result = calc.check_w_y(0.0100, 0.0100)
        assert result['equivalent'] == True
        assert result['rule'] == 'W/Y'
    
    def test_check_w_y_different(self):
        """W ≠ Y."""
        calc = ProportionsCalculator()
        result = calc.check_w_y(0.0100, 0.0140)
        assert result['equivalent'] == False
    
    def test_get_results_empty(self):
        """get_results после calculate_all с пустым списком."""
        calc = ProportionsCalculator()
        calc.calculate_all([], [])
        assert calc.get_results() == []
    
    def test_zero_division(self):
        """Деление на ноль обрабатывается."""
        calc = ProportionsCalculator()
        result = calc.check_w1_w3(0, 0.0100)
        assert result['ratio'] is None
        assert result['proportional'] == False
    
    def test_check_a_c_zero(self):
        """A = 0 — эквивалентность False."""
        calc = ProportionsCalculator()
        result = calc.check_a_c(0, 0.0100)
        assert result['ratio'] is None
        assert result['equivalent'] == False
    
    def test_check_w_y_zero(self):
        """W = 0 — эквивалентность False."""
        calc = ProportionsCalculator()
        result = calc.check_w_y(0, 0.0100)
        assert result['ratio'] is None



# ============================================================
# DIVERGENCE v2 (A/C, W/Y, AO, peak)
# ============================================================
class TestDivergenceV2:
    def make_df(self, n=100):
        """Данные со свечами."""
        np.random.seed(42)
        dates = [datetime(2026, 1, 1) + timedelta(hours=i) for i in range(n)]
        base = np.linspace(1.1000, 1.1500, n)
        noise = np.random.randn(n) * 0.0005
        prices = base + noise
        return pd.DataFrame({
            'open': prices,
            'high': prices + 0.0003,
            'low': prices - 0.0003,
            'close': prices,
            'tick_volume': [100] * n,
        }, index=dates)
    
    def test_ao_calculation(self):
        """AO рассчитывается."""
        df = self.make_df()
        detector = DivergenceDetector(df=df)
        assert detector.ao is not None
        assert len(detector.ao) == len(df)
    
    def test_ao_value_at(self):
        """AO значение в точке."""
        df = self.make_df()
        detector = DivergenceDetector(df=df)
        val = detector.get_ao_value_at(df.index[50])
        assert val is None or isinstance(val, float)
    
    def test_ac_divergence(self):
        """A/C дивергенция."""
        df = self.make_df()
        detector = DivergenceDetector(df=df)
        corr = {
            'type': 'zigzag', 'direction': 'bearish',
            'points': [
                (df.index[10], 1.1000, '0'),
                (df.index[20], 1.1050, 'A'),
                (df.index[30], 1.1020, 'B'),
                (df.index[40], 1.1080, 'C'),
            ],
        }
        result = detector.check_ac_divergence(corr)
        assert 'divergence' in result
        assert result['rule'] == 'A/C'
    
    def test_wy_divergence(self):
        """W/Y дивергенция."""
        df = self.make_df()
        detector = DivergenceDetector(df=df)
        combo = {
            'type': 'double_three', 'direction': 'bullish',
            'points': [
                (df.index[10], 1.1000, 'W'),
                (df.index[20], 1.1050, 'X'),
                (df.index[30], 1.1020, 'Y'),
                (df.index[40], 1.1080, 'Y_end'),
            ],
        }
        result = detector.check_wy_divergence(combo)
        assert 'divergence' in result
        assert result['rule'] == 'W/Y'
    
    def test_find_macd_peak(self):
        """Поиск пика MACD."""
        df = self.make_df()
        detector = DivergenceDetector(df=df)
        peak = detector.find_macd_peak(df.index[10], df.index[90])
        # Может быть None или dict
        assert peak is None or 'peak_time' in peak
    
    def test_find_ao_peak(self):
        """Поиск пика AO."""
        df = self.make_df()
        detector = DivergenceDetector(df=df)
        peak = detector.find_macd_peak(df.index[10], df.index[90], indicator='ao')
        assert peak is None or 'peak_time' in peak
    
    def test_calculate_all_with_corrections(self):
        """calculate_all с коррекциями."""
        df = self.make_df()
        detector = DivergenceDetector(df=df)
        imp = {
            'direction': 'bullish',
            'points': [
                (df.index[10], 1.1000, '0'),
                (df.index[20], 1.1050, '1'),
                (df.index[30], 1.1030, '2'),
                (df.index[40], 1.1100, '3'),
                (df.index[50], 1.1070, '4'),
                (df.index[60], 1.1150, '5'),
            ],
        }
        corr = {
            'type': 'zigzag', 'direction': 'bearish',
            'points': [
                (df.index[70], 1.1150, '0'),
                (df.index[80], 1.1100, 'A'),
                (df.index[85], 1.1120, 'B'),
                (df.index[90], 1.1080, 'C'),
            ],
        }
        results = detector.calculate_all([imp], [corr], [])
        assert len(results) >= 1
    
    def test_calculate_all_with_combinations(self):
        """calculate_all с комбинациями."""
        df = self.make_df()
        detector = DivergenceDetector(df=df)
        combo = {
            'type': 'double_three', 'direction': 'bullish',
            'points': [
                (df.index[10], 1.1000, 'W'),
                (df.index[20], 1.1050, 'X'),
                (df.index[30], 1.1020, 'Y'),
                (df.index[40], 1.1080, 'Y_end'),
            ],
        }
        results = detector.calculate_all([], [], [combo])
        assert len(results) == 1
    
    def test_no_data_ao(self):
        """Без df — AO no_data."""
        detector = DivergenceDetector(df=None)
        val = detector.get_ao_value_at(datetime(2026, 1, 1))
        assert val is None



# ============================================================
# EXTENSION — дополнительные тесты (для покрытия)
# ============================================================
class TestExtensionExtra:
    def test_w3_bearish(self):
        """W3 для медвежьего импульса."""
        calc = ExtensionCalculator()
        result = calc.calculate_w3_targets(1.1100, 1.1000, 1.1050)
        # direction = -1 (bearish)
        assert result['direction'] == 'bearish'
        assert 1.618 in result['targets']
        # 1.1050 - 0.0100 * 1.618 = 1.08882
        assert abs(result['targets'][1.618] - 1.08882) < 0.0001
    
    def test_w5_bearish(self):
        """W5 для медвежьего импульса."""
        calc = ExtensionCalculator()
        result = calc.calculate_w5_targets(1.1100, 1.0850, 1.0950)
        assert result['direction'] == 'bearish'
        assert 1.000 in result['targets']
    
    def test_calculate_all_bearish_impulse(self):
        """calculate_all для медвежьего импульса."""
        calc = ExtensionCalculator()
        impulse = {
            'points': [
                (None, 1.1100, '0'), (None, 1.1000, '1'),
                (None, 1.1050, '2'), (None, 1.0850, '3'),
                (None, 1.0950, '4'), (None, 1.0750, '5'),
            ],
            'direction': 'bearish',
        }
        results = calc.calculate_all([impulse], [])
        assert len(results) == 1
        assert 'w3' in results[0]
        assert 'w5' in results[0]
    
    def test_calculate_all_with_flat(self):
        """calculate_all с flat коррекцией."""
        calc = ExtensionCalculator()
        corr = {
            'type': 'flat', 'direction': 'bearish', 'subtype': 'expanded',
            'points': [
                (None, 1.1500, '0'), (None, 1.1450, 'A'),
                (None, 1.1550, 'B'), (None, 1.1350, 'C'),
            ],
        }
        results = calc.calculate_all([], [corr])
        assert len(results) == 1
        assert 'wc' in results[0]
        # flat_expanded -> только 1.618
        assert 1.618 in results[0]['wc']['targets']

# ============================================================
# ORTHODOX v2 (все паттерны)
# ============================================================
class TestOrthodoxV2:
    def test_orthodox_flat_running(self):
        """Бегущая плоскость — ортодоксальная = W_A."""
        detector = OrthodoxPointsDetector()
        flat = {
            'type': 'flat', 'subtype': 'running',
            'points': [
                (datetime(2026, 1, 1), 1.1500, '0'),
                (datetime(2026, 1, 2), 1.1450, 'A'),
                (datetime(2026, 1, 3), 1.1550, 'B'),
                (datetime(2026, 1, 4), 1.1460, 'C'),
            ],
        }
        time, price = detector.get_orthodox_end(flat)
        assert price == 1.1450, "Ортодоксальная точка = W_A"
    
    def test_orthodox_flat_regular(self):
        """Обычная плоскость — ортодоксальная = W_C."""
        detector = OrthodoxPointsDetector()
        flat = {
            'type': 'flat', 'subtype': 'regular',
            'points': [
                (datetime(2026, 1, 1), 1.1500, '0'),
                (datetime(2026, 1, 2), 1.1450, 'A'),
                (datetime(2026, 1, 3), 1.1500, 'B'),
                (datetime(2026, 1, 4), 1.1400, 'C'),
            ],
        }
        time, price = detector.get_orthodox_end(flat)
        assert price == 1.1400
    
    def test_orthodox_triangle(self):
        """Треугольник — ортодоксальная = E."""
        detector = OrthodoxPointsDetector()
        triangle = {
            'type': 'triangle', 'subtype': 'symmetric',
            'points': [
                (datetime(2026, 1, 1), 1.1500, 'A'),
                (datetime(2026, 1, 2), 1.1550, 'B'),
                (datetime(2026, 1, 3), 1.1520, 'C'),
                (datetime(2026, 1, 4), 1.1530, 'D'),
                (datetime(2026, 1, 5), 1.1510, 'E'),
            ],
        }
        time, price = detector.get_orthodox_end(triangle)
        assert price == 1.1510
    
    def test_orthodox_diagonal_truncated(self):
        """Конечная диагональ с усечением — ортодоксальная = W3."""
        detector = OrthodoxPointsDetector()
        diagonal = {
            'type': 'diagonal', 'truncated': True,
            'points': [
                (datetime(2026, 1, 1), 1.1000, '0'),
                (datetime(2026, 1, 2), 1.1100, '1'),
                (datetime(2026, 1, 3), 1.1050, '2'),
                (datetime(2026, 1, 4), 1.1300, '3'),
                (datetime(2026, 1, 5), 1.1200, '4'),
                (datetime(2026, 1, 6), 1.1280, '5'),
            ],
        }
        time, price = detector.get_orthodox_end(diagonal)
        assert price == 1.1300, "Ортодоксальная = W3 при усечении"
    
    def test_orthodox_combination(self):
        """Комбинация — ортодоксальная = последняя точка."""
        detector = OrthodoxPointsDetector()
        combo = {
            'type': 'double_three',
            'points': [
                (datetime(2026, 1, 1), 1.1000, 'W'),
                (datetime(2026, 1, 2), 1.1100, 'X'),
                (datetime(2026, 1, 3), 1.1050, 'Y'),
                (datetime(2026, 1, 4), 1.1150, 'Z'),
            ],
        }
        time, price = detector.get_orthodox_end(combo)
        assert price == 1.1150
    
    def test_universal_dispatch(self):
        """Универсальный метод работает для разных типов."""
        detector = OrthodoxPointsDetector()
        
        impulse = {
            'type': 'impulse', 'truncated': False,
            'points': [
                (datetime(2026, 1, 1), 1.1000, '0'),
                (datetime(2026, 1, 2), 1.1100, '1'),
                (datetime(2026, 1, 3), 1.1050, '2'),
                (datetime(2026, 1, 4), 1.1300, '3'),
                (datetime(2026, 1, 5), 1.1200, '4'),
                (datetime(2026, 1, 6), 1.1450, '5'),
            ],
        }
        time, price = detector.get_orthodox_end(impulse)
        assert price == 1.1450


# ============================================================
# EXTENSION v2 (W4 vs W2, диагонали)
# ============================================================
class TestExtensionV2:
    def test_w4_vs_w2_levels(self):
        """W4 vs W2 — 5 уровней."""
        calc = ExtensionCalculator()
        result = calc.calculate_w4_vs_w2(1.1000, 1.1050, 1.1100)
        assert result['wave'] == 'W4'
        assert len(result['targets']) == 5
        assert 0.618 in result['targets']
        assert 1.618 in result['targets']
    
    def test_w4_vs_w2_values(self):
        """W4 vs W2 — проверка расчёта."""
        calc = ExtensionCalculator()
        result = calc.calculate_w4_vs_w2(1.1000, 1.1050, 1.1100)
        # w2_len = 0.0050
        # 100% = 1.1100 + 0.0050 * 1.0 = 1.1150
        assert abs(result['targets'][1.000] - 1.1150) < 0.0001
        # 161.8% = 1.1100 + 0.0050 * 1.618 = 1.11809
        assert abs(result['targets'][1.618] - 1.11809) < 0.0001
    
    def test_diagonal_contracting(self):
        """Сужающаяся диагональ — 2 уровня."""
        calc = ExtensionCalculator()
        result = calc.calculate_diagonal_targets(1.1000, 1.1100, 1.1050, 'contracting')
        assert len(result['targets']) == 2
        assert 0.618 in result['targets']
        assert 0.786 in result['targets']
    
    def test_diagonal_expanding(self):
        """Расширяющаяся диагональ — 2 уровня."""
        calc = ExtensionCalculator()
        result = calc.calculate_diagonal_targets(1.1000, 1.1100, 1.1050, 'expanding')
        assert len(result['targets']) == 2
        assert 1.272 in result['targets']
        assert 1.618 in result['targets']
    
    def test_calculate_all_with_w4_vs_w2(self):
        """calculate_all включает w4_vs_w2."""
        calc = ExtensionCalculator()
        imp = {
            'points': [
                (None, 1.1000, '0'), (None, 1.1100, '1'),
                (None, 1.1050, '2'), (None, 1.1300, '3'),
                (None, 1.1200, '4'), (None, 1.1450, '5'),
            ],
            'direction': 'bullish',
        }
        results = calc.calculate_all([imp], [])
        assert len(results) == 1
        assert 'w4_vs_w2' in results[0]
        assert results[0]['w4_vs_w2']['wave'] == 'W4'
    
    def test_diagonal_levels_contracting(self):
        """Проверка уровней сужающейся диагонали."""
        calc = ExtensionCalculator()
        result = calc.calculate_diagonal_targets(1.1000, 1.1100, 1.1050, 'contracting')
        # w1_len = 0.0100
        # 61.8% = 1.1050 + 0.0100 * 0.618 = 1.11118
        assert abs(result['targets'][0.618] - 1.11118) < 0.0001


# ============================================================
# EXTENSION v2 (полные правила растяжения)
# ============================================================
class TestExtensionV2:
    def test_w1_extension_rule(self):
        """W1 растянута -> W5 = 61.8% от W1."""
        analyzer = ExtensionAnalyzer()
        result = analyzer.check_w1_extension(0.0100, 0.00618)
        assert result['valid'] == True
        assert result['rule'] == 'w1_extension_w5_61.8'
    
    def test_w1_extension_rule_invalid(self):
        """W1 растянута, но W5 сильно отличается."""
        analyzer = ExtensionAnalyzer()
        result = analyzer.check_w1_extension(0.0100, 0.0150)
        assert result['valid'] == False
    
    def test_w3_extension_rule(self):
        """W3 растянута -> W1 и W5 пропорциональны."""
        analyzer = ExtensionAnalyzer()
        result = analyzer.check_w3_extension(0.0100, 0.0110)
        assert result['valid'] == True
        assert result['rule'] == 'w3_extension_w1_w5_proportional'
    
    def test_w5_extension_rule(self):
        """W5 растянута -> W5 = 161.8% от W3."""
        analyzer = ExtensionAnalyzer()
        result = analyzer.check_w5_extension(0.0100, 0.01618)
        assert result['valid'] == True
        assert result['rule'] == 'w5_extension_161.8'
    
    def test_check_subwaves(self):
        """Растянутая волна содержит 5 подволн."""
        analyzer = ExtensionAnalyzer()
        imp = {'extension': 'W3'}
        result = analyzer.check_subwaves(imp)
        assert result['has_subwaves'] == True
        assert result['subwave_count'] == 5
        assert result['extension'] == 'W3'
    
    def test_calculate_all_w3_extension(self):
        """Расчёт с растянутой W3."""
        analyzer = ExtensionAnalyzer()
        # W1=0.0100, W2=0.0050, W3=0.0300 (растянута), W4=0.0050, W5=0.0100
        imp = {
            'direction': 'bullish',
            'points': [
                (datetime(2026, 1, 1), 1.1000, '0'),
                (datetime(2026, 1, 2), 1.1100, '1'),   # W1 = 0.0100
                (datetime(2026, 1, 3), 1.1050, '2'),   # W2 = 0.0050
                (datetime(2026, 1, 4), 1.1350, '3'),   # W3 = 0.0300 (растянута)
                (datetime(2026, 1, 5), 1.1300, '4'),   # W4 = 0.0050
                (datetime(2026, 1, 6), 1.1400, '5'),   # W5 = 0.0100
            ],
        }
        results = analyzer.calculate_all([imp])
        assert len(results) == 1
        assert results[0]['extension'] == 'W3'
        assert results[0]['rule_check'] is not None
        assert results[0]['subwave_check']['has_subwaves'] == True

class TestTriangleProportions:
    def test_triangle_contracting(self):
        """Сужающийся треугольник."""
        calc = ProportionsCalculator()
        result = calc.check_triangle_alternation(0.0100, 0.00618, 0.00482, 'contracting')
        assert result['rule'] == 'triangle_alternation'
    
    def test_triangle_expanding(self):
        """Расширяющийся треугольник."""
        calc = ProportionsCalculator()
        result = calc.check_triangle_alternation(0.0100, 0.01272, 0.01618, 'expanding')
        assert result['rule'] == 'triangle_alternation'
    
    def test_triangle_zero_a(self):
        """A = 0 -> невалидно."""
        calc = ProportionsCalculator()
        result = calc.check_triangle_alternation(0, 0.0100, 0.0100, 'contracting')
        assert result['valid'] == False

