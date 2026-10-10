"""
Chart Fib - Визуализация уровней Фибоначчи.
С вертикальными линиями и улучшенными подписями.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FibVisualizer:
    """Отрисовка уровней Фибо на графике."""
    
    # Цвета
    COLOR_RETRACEMENT = '#FFA500'   # оранжевый
    COLOR_EXTENSION = '#00FF88'     # зелёный
    COLOR_CLUSTER = '#FFD700'       # золотой
    
    # Приоритетные уровни (показываем только их)
    KEY_RETRACEMENT = [0.500, 0.618, 0.786]      # для W2
    KEY_RETRACEMENT_W4 = [0.382, 0.500]          # для W4
    KEY_EXTENSION = [1.000, 1.618]               # для W3/W5
    KEY_WC = [1.000, 1.618]                      # для W_C
    
    def __init__(self):
        self.retracement_count = 0
        self.extension_count = 0
        self.cluster_count = 0
    
    def _filter_levels(self, wave, levels, is_retracement):
        """Фильтрует уровни — оставляет только ключевые."""
        if not levels:
            return {}
        
        filtered = {}
        for lvl, price in levels.items():
            if is_retracement:
                # Для W2 и W4 — ключевые уровни
                if wave == 'W2' and lvl in self.KEY_RETRACEMENT:
                    filtered[lvl] = price
                elif wave == 'W4' and lvl in self.KEY_RETRACEMENT_W4:
                    filtered[lvl] = price
                elif wave == 'W_B':
                    if lvl in [0.500, 0.618, 0.900]:
                        filtered[lvl] = price
            else:
                # Для extension — ключевые цели
                if wave in ['W3', 'W5'] and lvl in self.KEY_EXTENSION:
                    filtered[lvl] = price
                elif wave == 'W_C' and lvl in self.KEY_WC:
                    filtered[lvl] = price
        
        return filtered
    
    def plot_retracement(self, ax, retracement_result, time_start, time_end):
        """Рисует уровни отката с вертикальными линиями."""
        if not retracement_result or 'levels' not in retracement_result:
            return
        
        wave = retracement_result.get('wave', '?')
        filtered = self._filter_levels(wave, retracement_result['levels'], True)
        
        for lvl, price in filtered.items():
            if price is None or pd.isna(price):
                continue
            
            # Горизонтальная линия
            ax.hlines(
                y=price,
                xmin=time_start,
                xmax=time_end,
                colors=self.COLOR_RETRACEMENT,
                linestyles='--',
                linewidth=1.5,
                alpha=0.85,
                zorder=2,
            )
            
            # Вертикальный пунктир (от начала до уровня)
            ax.axvline(
                x=time_start,
                color=self.COLOR_RETRACEMENT,
                linestyle=':',
                linewidth=0.8,
                alpha=0.4,
                zorder=1,
            )
            
            # Подпись справа с фоном
            label = f'{wave} {lvl*100:.1f}%'
            ax.annotate(
                label,
                xy=(time_end, price),
                xytext=(5, 0),
                textcoords='offset points',
                fontsize=9,
                color='black',
                fontweight='bold',
                va='center',
                ha='left',
                bbox=dict(
                    boxstyle='round,pad=0.3',
                    facecolor=self.COLOR_RETRACEMENT,
                    edgecolor='white',
                    linewidth=1.0,
                    alpha=0.9,
                ),
                zorder=10,
            )
            self.retracement_count += 1
    
    def plot_extension(self, ax, extension_result, time_start, time_end):
        """Рисует цели расширения."""
        if not extension_result or 'targets' not in extension_result:
            return
        
        wave = extension_result.get('wave', '?')
        filtered = self._filter_levels(wave, extension_result['targets'], False)
        
        for lvl, price in filtered.items():
            if price is None or pd.isna(price):
                continue
            
            ax.hlines(
                y=price,
                xmin=time_start,
                xmax=time_end,
                colors=self.COLOR_EXTENSION,
                linestyles=':',
                linewidth=1.5,
                alpha=0.85,
                zorder=2,
            )
            
            label = f'{wave} {lvl*100:.1f}%'
            ax.annotate(
                label,
                xy=(time_end, price),
                xytext=(5, 0),
                textcoords='offset points',
                fontsize=9,
                color='black',
                fontweight='bold',
                va='center',
                ha='left',
                bbox=dict(
                    boxstyle='round,pad=0.3',
                    facecolor=self.COLOR_EXTENSION,
                    edgecolor='white',
                    linewidth=1.0,
                    alpha=0.9,
                ),
                zorder=10,
            )
            self.extension_count += 1
    
    def plot_clusters(self, ax, clusters, time_start, time_end):
        """Рисует зоны кластеров."""
        for cluster in clusters:
            if cluster['strength'] < 2:
                continue
            
            alpha = min(0.15 + cluster['strength'] * 0.05, 0.35)
            
            ax.axhspan(
                cluster['zone_low'],
                cluster['zone_high'],
                color=self.COLOR_CLUSTER,
                alpha=alpha,
                zorder=1.5,
            )
            
            ax.annotate(
                f"★ x{cluster['strength']}",
                xy=(time_start, cluster['center']),
                xytext=(-50, 0),
                textcoords='offset points',
                fontsize=10,
                color='black',
                fontweight='bold',
                va='center',
                bbox=dict(
                    boxstyle='round,pad=0.3',
                    facecolor=self.COLOR_CLUSTER,
                    edgecolor='white',
                    linewidth=1.0,
                ),
                zorder=10,
            )
            self.cluster_count += 1
    
    def plot_all(self, ax, fib_results, clusters, time_range):
        """Отрисовка всех уровней."""
        time_start, time_end = time_range
        
        for r in fib_results:
            if 'levels' in r:
                self.plot_retracement(ax, r, time_start, time_end)
            elif 'targets' in r:
                self.plot_extension(ax, r, time_start, time_end)
        
        if clusters:
            self.plot_clusters(ax, clusters, time_start, time_end)
    
    def get_summary(self):
        return {
            'retracement_lines': self.retracement_count,
            'extension_lines': self.extension_count,
            'cluster_zones': self.cluster_count,
        }
