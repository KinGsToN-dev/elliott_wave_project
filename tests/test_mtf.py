"""
Тесты для mtf.multi_timeframe и mtf.panel_builder.
"""
import pytest
import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mtf.multi_timeframe import MultiTimeframeAnalyzer, TIMEFRAMES, TF_ORDER
from mtf.panel_builder import PanelBuilder


def make_df(n=500, trend='up'):
    """Хелпер: создаёт DataFrame со свечами."""
    np.random.seed(42)
    dates = [datetime(2026, 1, 1) + timedelta(hours=i) for i in range(n)]
    
    if trend == 'up':
        base = np.linspace(1.1000, 1.1500, n)
    elif trend == 'down':
        base = np.linspace(1.1500, 1.1000, n)
    else:
        base = np.ones(n) * 1.1000
    
    noise = np.random.randn(n) * 0.0005
    prices = base + noise
    
    df = pd.DataFrame({
        'open': prices,
        'high': prices + abs(np.random.randn(n) * 0.0003),
        'low': prices - abs(np.random.randn(n) * 0.0003),
        'close': prices + np.random.randn(n) * 0.0002,
        'tick_volume': np.random.randint(100, 1000, n),
    }, index=dates)
    return df


class TestMultiTimeframeAnalyzer:
    def test_init(self):
        """Инициализация."""
        mtf = MultiTimeframeAnalyzer(symbol='EURUSD', candles_count=500)
        assert mtf.symbol == 'EURUSD'
        assert mtf.candles_count == 500
        assert mtf.results == {}
    
    def test_get_zigzag_length(self):
        """Длина ZigZag для разных ТФ."""
        mtf = MultiTimeframeAnalyzer()
        assert mtf._get_zigzag_length('M15') == 3
        assert mtf._get_zigzag_length('H1') == 5
        assert mtf._get_zigzag_length('W1') == 3
    
    def test_determine_trend_bullish(self):
        """Тренд BULLISH — цена выше EMA."""
        mtf = MultiTimeframeAnalyzer()
        df = make_df(500, 'up')
        trend = mtf._determine_trend(df)
        assert trend in ['BULLISH', 'NEUTRAL']
    
    def test_determine_trend_bearish(self):
        """Тренд BEARISH — цена ниже EMA."""
        mtf = MultiTimeframeAnalyzer()
        df = make_df(500, 'down')
        trend = mtf._determine_trend(df)
        assert trend in ['BEARISH', 'NEUTRAL']
    
    def test_analyze_tf_empty(self):
        """Пустой df — None."""
        mtf = MultiTimeframeAnalyzer()
        result = mtf.analyze_tf(None, 'H1')
        assert result is None
    
    def test_analyze_tf_small(self):
        """Маленький df — None (меньше 20)."""
        mtf = MultiTimeframeAnalyzer()
        df = make_df(10)
        result = mtf.analyze_tf(df, 'H1')
        assert result is None
    
    def test_analyze_tf_valid(self):
        """Валидный df — возвращает dict."""
        mtf = MultiTimeframeAnalyzer()
        df = make_df(500)
        result = mtf.analyze_tf(df, 'H1')
        assert result is not None
        assert result['tf'] == 'H1'
        assert 'current_wave' in result
        assert 'trend' in result
    
    def test_determine_current_wave_empty(self):
        """Пустые паттерны — '?'."""
        mtf = MultiTimeframeAnalyzer()
        result = mtf._determine_current_wave([], [], [], None)
        assert result['wave'] == '?'
    
    def test_determine_current_wave_with_impulse(self):
        """С импульсом — определяет волну."""
        mtf = MultiTimeframeAnalyzer()
        impulse = {
            'end_time': datetime(2026, 1, 10),
            'points': [
                (datetime(2026, 1, 1), 1.1000, '0'),
                (datetime(2026, 1, 2), 1.1100, '1'),
                (datetime(2026, 1, 3), 1.1050, '2'),
                (datetime(2026, 1, 4), 1.1300, '3'),
                (datetime(2026, 1, 5), 1.1200, '4'),
                (datetime(2026, 1, 10), 1.1450, '5'),
            ],
            'direction': 'bullish',
            'size': 0.045,
        }
        result = mtf._determine_current_wave([impulse], [], [], None)
        assert result['wave'] == '(5)'
        assert result['pattern'] == 'impulse'
    
    def test_get_global_trend_no_w1(self):
        """Нет W1 — UNKNOWN."""
        mtf = MultiTimeframeAnalyzer()
        assert mtf.get_global_trend() == 'UNKNOWN'
    
    def test_analyze_all_empty_loader(self):
        """data_loader возвращает None — пустой результат."""
        mtf = MultiTimeframeAnalyzer()
        
        def loader(tf, count):
            return None
        
        results = mtf.analyze_all(loader)
        assert results == {}
    
    def test_analyze_all_valid(self):
        """Валидный loader — все ТФ."""
        mtf = MultiTimeframeAnalyzer(candles_count=300)
        df = make_df(300)
        
        def loader(tf, count):
            return df
        
        results = mtf.analyze_all(loader)
        assert len(results) >= 1


class TestPanelBuilder:
    def test_init(self):
        """Инициализация."""
        pb = PanelBuilder({})
        assert pb.rows == []
    
    def test_build_rows_empty(self):
        """Пустые данные — пустая таблица."""
        pb = PanelBuilder({})
        rows = pb.build_rows()
        assert rows == []
    
    def test_build_rows_with_data(self):
        """Данные с H1 — одна строка."""
        mtf_results = {
            'H1': {
                'current_wave': {'wave': '(3)', 'pattern': 'impulse', 'direction': 'bullish'},
                'trend': 'BULLISH',
            },
        }
        pb = PanelBuilder(mtf_results)
        rows = pb.build_rows()
        assert len(rows) == 1
        assert rows[0]['tf'] == 'H1'
        assert rows[0]['wave'] == '(3)'
    
    def test_print_console(self):
        """print_console не падает."""
        mtf_results = {
            'H1': {
                'current_wave': {'wave': '(3)', 'pattern': 'impulse', 'direction': 'bullish'},
                'trend': 'BULLISH',
            },
        }
        pb = PanelBuilder(mtf_results)
        pb.print_console()  # не должно упасть
    
    def test_get_dataframe(self):
        """get_dataframe возвращает DataFrame."""
        mtf_results = {
            'H1': {
                'current_wave': {'wave': '(3)', 'pattern': 'impulse', 'direction': 'bullish'},
                'trend': 'BULLISH',
            },
        }
        pb = PanelBuilder(mtf_results)
        df = pb.get_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
    
    def test_get_summary(self):
        """get_summary возвращает сводку."""
        mtf_results = {
            'W1': {
                'current_wave': {'wave': '(I)', 'pattern': 'impulse', 'direction': 'bullish'},
                'trend': 'BULLISH',
            },
            'H1': {
                'current_wave': {'wave': '(3)', 'pattern': 'impulse', 'direction': 'bullish'},
                'trend': 'BULLISH',
            },
        }
        pb = PanelBuilder(mtf_results)
        summary = pb.get_summary()
        assert summary['total_tf'] == 2
        assert summary['global_trend'] == 'BULLISH'
