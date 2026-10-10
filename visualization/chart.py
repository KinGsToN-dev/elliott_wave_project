"""
Chart - Визуализация импульсов и диагоналей с метками волн.
"""
import pandas as pd
import numpy as np
from lightweight_charts import Chart
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class EWChart:
    def __init__(self, title="Elliott Wave Chart"):
        self.chart = Chart(title=title)
        self._label_counter = 0
    
    def load_data(self, df):
        df_chart = df.reset_index()
        df_chart = df_chart.rename(columns={
            df_chart.columns[0]: 'time',
            'open': 'open', 'high': 'high', 'low': 'low',
            'close': 'close', 'tick_volume': 'volume'
        })
        df_chart = df_chart[['time', 'open', 'high', 'low', 'close', 'volume']]
        df_chart['time'] = pd.to_datetime(df_chart['time']).dt.strftime('%Y-%m-%d %H:%M:%S')
        df_chart = df_chart.sort_values('time').reset_index(drop=True)
        self.chart.set(df_chart)
        print(f"[OK] Данные загружены: {len(df_chart)} свечей.")
    
    def add_zigzag(self, pivots, color='#FFD700', width=1):
        if pivots is None or len(pivots) < 2:
            return
        line = self.chart.create_line(name='ZigZag', color=color, width=width, style='solid')
        line_data = pd.DataFrame({
            'time': pd.to_datetime(pivots.index).strftime('%Y-%m-%d %H:%M:%S'),
            'ZigZag': pivots['price'].values
        }).sort_values('time').reset_index(drop=True)
        line.set(line_data)
        print(f"[OK] ZigZag добавлен: {len(line_data)} точек.")
    
    def _add_pattern(self, patterns, prefix, color_bull, color_bear, max_show):
        """Универсальный метод для отрисовки паттернов."""
        if not patterns:
            return
        shown = patterns[-max_show:]
        for idx, p in enumerate(shown):
            direction = p['direction']
            color = color_bull if direction == 'bullish' else color_bear
            size_factor = min(p['size'] / 0.01, 4.0)
            width = int(2 + size_factor)
            line_name = f"{prefix}_{idx}_{p['start_time'].strftime('%Y%m%d%H%M')}"
            line = self.chart.create_line(name=line_name, color=color, width=width, style='solid')
            times = [pd.to_datetime(pt[0]).strftime('%Y-%m-%d %H:%M:%S') for pt in p['points']]
            prices = [pt[1] for pt in p['points']]
            df = pd.DataFrame({'time': times, line_name: prices}).sort_values('time').reset_index(drop=True)
            line.set(df)
    
    def add_impulses(self, impulses, max_show=5):
        self._add_pattern(impulses, 'Impulse', '#00FF88', '#FF3366', max_show)
        print(f"[OK] Отрисовано импульсов: {len(impulses[-max_show:])}")
    
    def add_diagonals(self, diagonals, max_show=5):
        self._add_pattern(diagonals, 'Diagonal', '#00BFFF', '#FF00FF', max_show)
        print(f"[OK] Отрисовано диагоналей: {len(diagonals[-max_show:])}")
    
    def _add_labels_as_markers(self, patterns, max_show, prefix_text=''):
        """
        Отрисовка меток (1)-(5) через отдельные ТОЧКИ (маркеры).
        Каждая метка — это короткий вертикальный отрезок + точка на пивоте.
        """
        if not patterns:
            return
        shown = patterns[-max_show:]
        markers_count = 0
        
        for p in shown:
            direction = p['direction']
            for pt in p['points']:
                time, price, label = pt[0], pt[1], pt[2]
                if label == '0':
                    continue
                
                # Создаём точку-метку: короткий вертикальный отрезок
                # вверх для bearish, вниз для bullish
                if direction == 'bearish':
                    price_offset = 0.0003  # отступ вверх
                else:
                    price_offset = -0.0003  # отступ вниз
                
                marker_name = f"{prefix_text}_{label}_{self._label_counter}"
                self._label_counter += 1
                
                line = self.chart.create_line(
                    name=marker_name,
                    color='#FFFFFF' if direction == 'bullish' else '#FFFF00',
                    width=2,
                    style='solid'
                )
                
                # Время в двух точках (одно и то же, но с разной ценой → вертикальный отрезок)
                t_str = pd.to_datetime(time).strftime('%Y-%m-%d %H:%M:%S')
                
                df = pd.DataFrame({
                    'time': [t_str, t_str],
                    marker_name: [price, price + price_offset]
                })
                line.set(df)
                markers_count += 1
        
        print(f"[OK] Отрисовано меток-маркеров: {markers_count}")
    
    def add_wave_labels(self, impulses, max_show=5):
        """Метки для импульсов."""
        self._add_labels_as_markers(impulses, max_show, prefix_text='W')
    
    def add_diagonal_labels(self, diagonals, max_show=5):
        """Метки для диагоналей."""
        self._add_labels_as_markers(diagonals, max_show, prefix_text='D')
    
    def show(self):
        self.chart.show(block=True)
