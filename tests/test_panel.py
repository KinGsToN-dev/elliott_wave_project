"""
Тесты для visualization.panel.MTFPanel
"""
import pytest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from visualization.panel import MTFPanel


def make_panel_data():
    """Хелпер: данные для панели."""
    return [
        {'tf': 'M15', 'wave': '(iii)', 'pattern': 'impulse', 'direction': '↑ Bull', 'trend': '🟢', 'trend_raw': 'BULLISH'},
        {'tf': 'H1',  'wave': '(3)',   'pattern': 'impulse', 'direction': '↑ Bull', 'trend': '🟢', 'trend_raw': 'BULLISH'},
        {'tf': 'H4',  'wave': '(I)',   'pattern': 'impulse', 'direction': '↑ Bull', 'trend': '🟢', 'trend_raw': 'BULLISH'},
        {'tf': 'D1',  'wave': '(1)',   'pattern': 'diagonal', 'direction': '↑ Bull', 'trend': '🟢', 'trend_raw': 'BULLISH'},
        {'tf': 'W1',  'wave': '(I)',   'pattern': 'impulse', 'direction': '↑ Bull', 'trend': '🟢', 'trend_raw': 'BULLISH'},
    ]


class TestMTFPanel:
    def test_init(self):
        """Инициализация панели."""
        data = make_panel_data()
        panel = MTFPanel(data, global_trend='BULLISH')
        assert panel.panel_data == data
        assert panel.global_trend == 'BULLISH'
    
    def test_get_trend_color_bullish(self):
        """Цвет для BULLISH."""
        panel = MTFPanel([], global_trend='BULLISH')
        color = panel._get_trend_color('BULLISH')
        assert color == panel.COLOR_BULL
    
    def test_get_trend_color_bearish(self):
        """Цвет для BEARISH."""
        panel = MTFPanel([], global_trend='BEARISH')
        color = panel._get_trend_color('BEARISH')
        assert color == panel.COLOR_BEAR
    
    def test_get_direction_color(self):
        """Цвет для направления."""
        panel = MTFPanel([], global_trend='BULLISH')
        assert panel._get_direction_color('↑ Bull') == panel.COLOR_BULL
        assert panel._get_direction_color('↓ Bear') == panel.COLOR_BEAR
    
    def test_print_console(self, capsys):
        """print_console выводит данные."""
        data = make_panel_data()
        panel = MTFPanel(data, global_trend='BULLISH')
        panel.print_console()
        
        captured = capsys.readouterr()
        assert 'MTF ПАНЕЛЬ' in captured.out
        assert 'BULLISH' in captured.out
        assert 'M15' in captured.out
        assert 'H1' in captured.out
    
    def test_show_empty(self):
        """Пустая панель — не падает."""
        panel = MTFPanel([], global_trend='UNKNOWN')
        panel.show()  # просто не должно упасть
        panel.print_console()  # пустой вывод
