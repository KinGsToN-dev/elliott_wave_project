"""
Продвинутые тесты для live.monitor.

Покрывают: analyze, generate_signals (с MTF), run.
"""
import pytest
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from live.monitor import MarketMonitor


def make_df(n=100):
    start = datetime.now() - timedelta(hours=n)
    np.random.seed(42)
    dates = [start + timedelta(hours=i) for i in range(n)]
    prices = [1.1000 + np.random.randn() * 0.001 for _ in range(n)]
    return pd.DataFrame({
        'open': prices,
        'high': [p + 0.0005 for p in prices],
        'low': [p - 0.0005 for p in prices],
        'close': prices,
        'tick_volume': [100] * n,
    }, index=dates)


class TestAnalyze:
    def test_analyze_full_pipeline(self, mocker):
        """analyze проходит весь пайплайн с моками детекторов."""
        mock_zigzag = MagicMock()
        mock_zigzag.find_pivots.return_value = []
        mocker.patch('live.monitor.ZigZag', return_value=mock_zigzag)
        
        mock_impulse = MagicMock()
        mock_impulse.find_impulses.return_value = []
        mocker.patch('live.monitor.ImpulseDetector', return_value=mock_impulse)
        
        mock_diag = MagicMock()
        mock_diag.find_diagonals.return_value = []
        mocker.patch('live.monitor.DiagonalDetector', return_value=mock_diag)
        
        mock_corr = MagicMock()
        mock_corr.find_corrections.return_value = []
        mocker.patch('live.monitor.CorrectionDetector', return_value=mock_corr)
        
        mock_filter = MagicMock()
        mock_filter.filter.return_value = ([], [], [])
        mocker.patch('live.monitor.OverlapFilter', return_value=mock_filter)
        
        monitor = MarketMonitor(symbol='EURUSD', mode='swing')
        df = make_df(50)
        
        pivots, imps, diags, corrs = monitor.analyze(df)
        
        assert pivots == []
        assert imps == []
        assert diags == []
        assert corrs == []
        mock_zigzag.find_pivots.assert_called_once()
        mock_filter.filter.assert_called_once()


class TestGenerateSignalsWithMTF:
    def test_mtf_filter_applied(self, mocker):
        """generate_signals применяет MTF-фильтр, если включен."""
        mocker.patch('live.monitor.MT5_AVAILABLE', True)
        mock_connector_cls = mocker.patch('live.monitor.MT5Connector')
        mock_connector = MagicMock()
        mock_connector.connect.return_value = True
        mock_connector.get_candles.return_value = make_df(50)
        mock_connector_cls.return_value = mock_connector
        
        mock_mtf_filter_cls = mocker.patch('live.monitor.MTFFilter')
        mock_mtf_filter = MagicMock()
        mock_mtf_filter.filter_signals.side_effect = lambda sigs: sigs
        mock_mtf_filter_cls.return_value = mock_mtf_filter
        
        monitor = MarketMonitor(symbol='EURUSD', mode='intraday')
        df = make_df(50)
        
        # Стратегия возвращает сигнал
        test_signal = {
            'symbol': 'EURUSD', 'mode': 'intraday', 'strategy': 'combined',
            'direction': 'BUY', 'entry_price': 1.1000, 'target': 1.1100,
            'stop': 1.0950, 'pattern': 'W2',
        }
        mock_strategy = MagicMock()
        mock_strategy.generate_signals.return_value = [test_signal]
        mocker.patch('live.monitor.get_strategy', return_value=lambda: mock_strategy)
        
        signals = monitor.generate_signals(df, [], [], [])
        
        # MTF-фильтр вызван
        mock_mtf_filter.update_trend.assert_called_once()
        mock_mtf_filter.filter_signals.assert_called()


class TestRunLoop:
    def test_run_stops_after_max_iterations(self, mocker):
        """run останавливается после max_iterations."""
        mocker.patch('live.monitor.time.sleep')
        mocker.patch.object(MarketMonitor, 'run_once', return_value=[])
        
        monitor = MarketMonitor(symbol='EURUSD', mode='swing')
        
        # Собираем все yield'ы
        results = list(monitor.run(max_iterations=3))
        
        assert results == []

    def test_run_yields_signals(self, mocker):
        """run возвращает сигналы, если они есть."""
        mocker.patch('live.monitor.time.sleep')
        
        test_signal = {'symbol': 'EURUSD', 'direction': 'BUY'}
        mocker.patch.object(MarketMonitor, 'run_once', return_value=[test_signal])
        
        monitor = MarketMonitor(symbol='EURUSD', mode='swing')
        
        results = list(monitor.run(max_iterations=2))
        
        assert len(results) == 2  # 2 итерации, каждая с сигналом
        assert results[0] == [test_signal]

    def test_run_handles_keyboard_interrupt(self, mocker):
        """run ловит KeyboardInterrupt."""
        mocker.patch('live.monitor.time.sleep', side_effect=KeyboardInterrupt)
        
        monitor = MarketMonitor(symbol='EURUSD', mode='swing')
        
        # Не должно выбросить исключение
        result = list(monitor.run())
        assert result == []