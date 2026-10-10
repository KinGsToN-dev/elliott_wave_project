"""
Chart Structure - Волновая структура с уровнями Фибо.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class StructureChart:
    def __init__(self, title="Elliott Wave Structure", figsize=(18, 10)):
        self.title = title
        self.figsize = figsize
        self.fig = None
        self.ax = None
    
    def show(self, df, pivots=None, impulses=None, diagonals=None, corrections=None,
             fib_results=None, clusters=None, max_show=5):
        fig, ax = plt.subplots(figsize=self.figsize)
        fig.patch.set_facecolor('#0d1117')
        ax.set_facecolor('#0d1117')
        
        all_prices = []
        if pivots is not None:
            all_prices.extend(pivots['price'].values)
        if not all_prices:
            print("[WARNING] Нет данных для отрисовки.")
            return
        
        price_min = min(all_prices)
        price_max = max(all_prices)
        price_range = price_max - price_min
        offset = price_range * 0.025
        
        # 1. ZigZag
        if pivots is not None and len(pivots) >= 2:
            times = pd.to_datetime(pivots.index)
            prices = pivots['price'].values
            ax.plot(times, prices, color='#888888', linewidth=0.8,
                    alpha=0.4, zorder=1, label='ZigZag (фон)')
        
        # 2. Коррекции
        if corrections:
            shown = corrections[-max_show:]
            self._plot_corrections(ax, shown, offset)
        
        # 3. Диагонали
        if diagonals:
            shown = diagonals[-max_show:]
            for d in shown:
                color = '#00BFFF' if d['direction'] == 'bullish' else '#FF00FF'
                times = [pd.to_datetime(pt[0]) for pt in d['points']]
                prices = [pt[1] for pt in d['points']]
                ax.plot(times, prices, color=color, linewidth=2.0,
                        alpha=0.7, linestyle='--', zorder=3,
                        label=f"Диагональ {d['shape']}")
            self._plot_diagonal_labels(ax, shown, offset)
        
        # 4. Импульсы
        if impulses:
            shown = impulses[-max_show:]
            for imp in shown:
                color = '#00FF88' if imp['direction'] == 'bullish' else '#FF3366'
                times = [pd.to_datetime(pt[0]) for pt in imp['points']]
                prices = [pt[1] for pt in imp['points']]
                width = min(2 + imp['size'] / 0.005, 5)
                ax.plot(times, prices, color=color, linewidth=width,
                        alpha=1.0, zorder=5,
                        label=f"{'Бычий' if imp['direction']=='bullish' else 'Медвежий'} импульс")
            self._plot_impulse_labels(ax, shown, offset)
        
        # 5. ФИБОНАЧЧИ
        if fib_results:
            from visualization.chart_fib import FibVisualizer
            fib_viz = FibVisualizer()
            time_start = df.index[0]
            time_end = df.index[-1]
            fib_viz.plot_all(ax, fib_results, clusters or [], (time_start, time_end))
            summary = fib_viz.get_summary()
            print(f"[OK] Фибо: {summary['retracement_lines']} уровней, "
                  f"{summary['extension_lines']} целей, "
                  f"{summary['cluster_zones']} кластеров")
        
        # Оформление
        ax.set_title(self.title, color='white', fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Time', color='white', fontsize=12)
        ax.set_ylabel('Price', color='white', fontsize=12)
        ax.tick_params(colors='white', labelsize=10)
        ax.grid(True, color='#1a1a1a', linestyle='--', linewidth=0.5)
        
        for spine in ax.spines.values():
            spine.set_color('#444444')
        
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', color='white')
        
        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        if by_label:
            leg = ax.legend(by_label.values(), by_label.keys(),
                          loc='upper left', facecolor='#1a1a1a',
                          edgecolor='#444444', fontsize=9)
            plt.setp(leg.get_texts(), color='white')
        
        ax.set_ylim(price_min - price_range * 0.1, price_max + price_range * 0.1)
        
        self.fig = fig
        self.ax = ax
        plt.tight_layout()
        fig.canvas.draw()
        plt.show()
    
    def _plot_impulse_labels(self, ax, impulses, offset):
        for imp in impulses:
            direction = imp['direction']
            for pt in imp['points']:
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
                    f'({label})', xy=(t, price), xytext=(t, y_offset),
                    fontsize=16, fontweight='bold', color='black',
                    ha='center', va='center',
                    bbox=dict(boxstyle='circle,pad=0.5', facecolor=color,
                             edgecolor='white', linewidth=2.5),
                    zorder=20
                )
    
    def _plot_diagonal_labels(self, ax, diagonals, offset):
        for d in diagonals:
            direction = d['direction']
            for pt in d['points']:
                time, price, label = pt[0], pt[1], pt[2]
                if label == '0':
                    continue
                t = pd.to_datetime(time)
                if direction == 'bearish':
                    y_offset = price + offset * 1.3
                    color = '#FF00FF'
                else:
                    y_offset = price - offset * 1.3
                    color = '#00BFFF'
                ax.annotate(
                    f'D({label})', xy=(t, price), xytext=(t, y_offset),
                    fontsize=10, fontweight='bold', color='white',
                    ha='center', va='center',
                    bbox=dict(boxstyle='round,pad=0.25', facecolor=color,
                             edgecolor='white', linewidth=1.5),
                    zorder=19
                )
    
    def _plot_corrections(self, ax, corrections, offset):
        colors = {
            'zigzag': '#FFA500',
            'flat': '#FFD700',
            'triangle': '#9370DB',
        }
        for c in corrections:
            color = colors.get(c['type'], '#FFFFFF')
            times = [pd.to_datetime(pt[0]) for pt in c['points']]
            prices = [pt[1] for pt in c['points']]
            ax.plot(times, prices, color=color, linewidth=1.5,
                    alpha=0.6, linestyle=':', zorder=2,
                    label=f"{c['type']}")
            
            for pt in c['points']:
                time, price, label = pt[0], pt[1], pt[2]
                if label == '0':
                    continue
                t = pd.to_datetime(time)
                y_off = price - offset * 0.5 if c['direction'] != 'bearish' else price + offset * 0.5
                ax.annotate(
                    f'({label})', xy=(t, price), xytext=(t, y_off),
                    fontsize=9, fontweight='bold', color='black',
                    ha='center', va='center',
                    bbox=dict(boxstyle='round,pad=0.2', facecolor=color,
                             edgecolor='#333333', linewidth=1.0),
                    zorder=15
                )
    
    def save(self, filename='structure.png'):
        if self.fig:
            self.fig.savefig(filename, dpi=150, bbox_inches='tight',
                           facecolor='#0d1117')
            print(f"[OK] Структура сохранена: {filename}")
