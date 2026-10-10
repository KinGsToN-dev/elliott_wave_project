"""
Panel - MTF-панель для отображения состояния всех таймфреймов.
"""
import matplotlib.pyplot as plt
import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MTFPanel:
    """Панель MTF — таблица с волнами на каждом ТФ."""
    
    COLOR_BG = '#0d1117'
    COLOR_HEADER = '#1f2937'
    COLOR_TEXT = 'white'
    COLOR_BULL = '#00FF88'
    COLOR_BEAR = '#FF3366'
    COLOR_NEUTRAL = '#888888'
    
    def __init__(self, panel_data, global_trend='UNKNOWN'):
        self.panel_data = panel_data
        self.global_trend = global_trend
        self.fig = None
    
    def _get_trend_color(self, trend_raw):
        if trend_raw == 'BULLISH':
            return self.COLOR_BULL
        elif trend_raw == 'BEARISH':
            return self.COLOR_BEAR
        return self.COLOR_NEUTRAL
    
    def _get_direction_color(self, direction):
        if 'Bull' in direction:
            return self.COLOR_BULL
        elif 'Bear' in direction:
            return self.COLOR_BEAR
        return self.COLOR_NEUTRAL
    
    def show(self):
        """Отображает панель в отдельном окне."""
        if not self.panel_data:
            print("[WARNING] Нет данных для панели")
            return
        
        n_rows = len(self.panel_data)
        
        fig, ax = plt.subplots(figsize=(10, n_rows * 0.6 + 2))
        fig.patch.set_facecolor(self.COLOR_BG)
        ax.set_facecolor(self.COLOR_BG)
        ax.axis('off')
        
        # Заголовок
        ax.text(0.5, 0.97, 'MTF PANEL — Elliott Wave',
                transform=ax.transAxes, fontsize=14, fontweight='bold',
                color='white', ha='center', va='top')
        
        headers = ['TF', 'Wave', 'Pattern', 'Direction', 'Trend']
        col_x = [0.02, 0.13, 0.28, 0.55, 0.83]
        
        y_start = 0.88
        y_step = 0.10
        
        # Header
        for h, x in zip(headers, col_x):
            ax.text(x, y_start, h, transform=ax.transAxes,
                    fontsize=11, fontweight='bold', color='#FFD700',
                    ha='left', va='center')
        
        # Horizontal line (через plot, а не axhline)
        ax.plot(
            [0.02, 0.98],
            [y_start - y_step / 2, y_start - y_step / 2],
            color='#444444', linewidth=1,
            transform=ax.transAxes, clip_on=False,
        )
        
        # Rows
        for i, row in enumerate(self.panel_data):
            y = y_start - (i + 1) * y_step
            
            ax.text(col_x[0], y, row['tf'], transform=ax.transAxes,
                    fontsize=11, color=self.COLOR_TEXT, ha='left', va='center',
                    fontweight='bold')
            ax.text(col_x[1], y, row['wave'], transform=ax.transAxes,
                    fontsize=11, color=self.COLOR_TEXT, ha='left', va='center')
            ax.text(col_x[2], y, row['pattern'], transform=ax.transAxes,
                    fontsize=10, color=self.COLOR_TEXT, ha='left', va='center')
            
            dir_color = self._get_direction_color(row['direction'])
            ax.text(col_x[3], y, row['direction'], transform=ax.transAxes,
                    fontsize=10, color=dir_color, ha='left', va='center',
                    fontweight='bold')
            
            trend_color = self._get_trend_color(row['trend_raw'])
            ax.text(col_x[4], y, row['trend'], transform=ax.transAxes,
                    fontsize=12, color=trend_color, ha='left', va='center',
                    fontweight='bold')
        
        # Global trend
        y_global = y_start - (n_rows + 1) * y_step
        trend_color = self._get_trend_color(self.global_trend)
        ax.text(0.5, y_global, f'GLOBAL TREND (W1): {self.global_trend}',
                transform=ax.transAxes, fontsize=12, fontweight='bold',
                color=trend_color, ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.4', facecolor='#1a1a1a',
                         edgecolor=trend_color, linewidth=2))
        
        self.fig = fig
        plt.tight_layout()
        plt.show()
    
    def save(self, filename='mtf_panel.png'):
        if self.fig:
            self.fig.savefig(filename, dpi=150, bbox_inches='tight',
                           facecolor=self.COLOR_BG)
            print(f"[OK] Панель сохранена: {filename}")
    
    def print_console(self):
        print()
        print("=" * 70)
        print(" MTF ПАНЕЛЬ — Elliott Wave")
        print("=" * 70)
        print(f"{'TF':<6} {'Wave':<8} {'Pattern':<12} {'Direction':<12} {'Trend':<10}")
        print("-" * 70)
        for row in self.panel_data:
            print(f"{row['tf']:<6} {row['wave']:<8} {row['pattern']:<12} "
                  f"{row['direction']:<12} {row['trend_raw']:<10}")
        print("=" * 70)
        print(f" GLOBAL TREND (W1): {self.global_trend}")
        print("=" * 70)
        print()
