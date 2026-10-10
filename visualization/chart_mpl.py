"""
Chart - Визуализация на mplfinance.
Исправлено: используем make_addplot() для линий.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import mplfinance as mpf
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class EWChart:
    def __init__(self, title="Elliott Wave Chart"):
        self.title = title
        self.fig = None
        self.axes = None
    
    def show(self, df, pivots=None, impulses=None, diagonals=None, max_show=5):
        df_plot = df.copy()
        df_plot.index = pd.to_datetime(df_plot.index)
        df_plot = df_plot.rename(columns={
            'open': 'Open', 'high': 'High', 'low': 'Low',
            'close': 'Close', 'tick_volume': 'Volume'
        })
        
        price_range = df_plot['High'].max() - df_plot['Low'].min()
        offset = price_range * 0.015
        
        # ============================================================
        # СОБИРАЕМ ВСЕ ДОБАВЛЯЕМЫЕ ЛИНИИ ЧЕРЕЗ make_addplot
        # ============================================================
        add_plots = []
        
        # --- ZigZag ---
        if pivots is not None and len(pivots) >= 2:
            zigzag_series = self._build_series(df_plot.index, pivots)
            add_plots.append(mpf.make_addplot(
                zigzag_series, color='#FFD700', width=1.5,
                panel=0, label='ZigZag'
            ))
        
        # --- Импульсы ---
        if impulses:
            shown = impulses[-max_show:]
            for i, imp in enumerate(shown):
                color = '#00FF88' if imp['direction'] == 'bullish' else '#FF3366'
                series = self._build_series_from_points(df_plot.index, imp['points'])
                add_plots.append(mpf.make_addplot(
                    series, color=color, width=3, panel=0,
                    label=f"{'Bull' if imp['direction']=='bullish' else 'Bear'} Impulse {i+1}"
                ))
        
        # --- Диагонали ---
        if diagonals:
            shown = diagonals[-max_show:]
            for i, d in enumerate(shown):
                color = '#00BFFF' if d['direction'] == 'bullish' else '#FF00FF'
                series = self._build_series_from_points(df_plot.index, d['points'])
                add_plots.append(mpf.make_addplot(
                    series, color=color, width=2.5, panel=0, linestyle='--',
                    label=f"Diagonal {i+1}"
                ))
        
        # ============================================================
        # СТРОИМ ГРАФИК С ДОБАВЛЕННЫМИ ЛИНИЯМИ
        # ============================================================
        fig, axes = mpf.plot(
            df_plot,
            type='candle',
            style='charles',
            volume=True,
            returnfig=True,
            figsize=(16, 9),
            title=self.title,
            ylabel='Price',
            ylabel_lower='Volume',
            addplot=add_plots if add_plots else None,
            tight_layout=True,
        )
        
        ax = axes[0]
        
        # Оформление
        ax.set_facecolor('#0d1117')
        fig.patch.set_facecolor('#0d1117')
        ax.tick_params(colors='white')
        ax.yaxis.label.set_color('white')
        ax.xaxis.label.set_color('white')
        ax.title.set_color('white')
        ax.grid(True, color='#333333', linestyle='--', linewidth=0.5)
        
        # ============================================================
        # МЕТКИ (1)-(5) — добавляем после построения
        # ============================================================
        if impulses:
            self._plot_labels(ax, impulses[-max_show:], offset)
        if diagonals:
            self._plot_diagonal_labels(ax, diagonals[-max_show:], offset)
        
        # Форматирование дат
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', color='white')
        
        self.fig = fig
        self.axes = axes
        
        # ВАЖНО: принудительно перерисовать
        fig.canvas.draw()
        plt.show()
    
    def _build_series(self, full_index, pivots):
        """Создаёт series для ZigZag, выровненную по всем свечам (NaN где нет пивота)."""
        series = pd.Series(index=full_index, dtype=float)
        for t, row in pivots.iterrows():
            t_aligned = pd.to_datetime(t)
            if t_aligned in series.index:
                series[t_aligned] = row['price']
        return series
    
    def _build_series_from_points(self, full_index, points):
        """Создаёт series из точек паттерна."""
        series = pd.Series(index=full_index, dtype=float)
        for pt in points:
            t = pd.to_datetime(pt[0])
            if t in series.index:
                series[t] = pt[1]
        return series
    
    def _plot_labels(self, ax, patterns, offset):
        """Рисует метки (1)-(5) на пивотах импульсов."""
        for p in patterns:
            direction = p['direction']
            for pt in p['points']:
                time, price, label = pt[0], pt[1], pt[2]
                if label == '0':
                    continue
                t = pd.to_datetime(time)
                
                if direction == 'bearish':
                    y_offset = price + offset
                    color = '#FF3366'
                else:
                    y_offset = price - offset
                    color = '#00FF88'
                
                ax.annotate(
                    f'({label})',
                    xy=(t, price),
                    xytext=(t, y_offset),
                    fontsize=14, fontweight='bold',
                    color='white',
                    ha='center', va='center',
                    bbox=dict(
                        boxstyle='circle,pad=0.4',
                        facecolor=color,
                        edgecolor='white',
                        linewidth=2,
                    ),
                    zorder=20
                )
    
    def _plot_diagonal_labels(self, ax, diagonals, offset):
        """Рисует метки (1)-(5) на диагоналях."""
        for d in diagonals:
            direction = d['direction']
            for pt in d['points']:
                time, price, label = pt[0], pt[1], pt[2]
                if label == '0':
                    continue
                t = pd.to_datetime(time)
                
                if direction == 'bearish':
                    y_offset = price + offset * 1.5
                    color = '#FF00FF'
                else:
                    y_offset = price - offset * 1.5
                    color = '#00BFFF'
                
                ax.annotate(
                    f'({label})',
                    xy=(t, price),
                    xytext=(t, y_offset),
                    fontsize=12, fontweight='bold',
                    color='white',
                    ha='center', va='center',
                    bbox=dict(
                        boxstyle='circle,pad=0.3',
                        facecolor=color,
                        edgecolor='white',
                        linewidth=1.5,
                    ),
                    zorder=19
                )
    
    def save(self, filename='chart.png'):
        if self.fig:
            self.fig.savefig(filename, dpi=150, bbox_inches='tight', facecolor='#0d1117')
            print(f"[OK] График сохранён: {filename}")
