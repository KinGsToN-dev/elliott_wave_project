"""
PanelBuilder - Построение данных для панели MTF.
"""
import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mtf.multi_timeframe import TF_ORDER


class PanelBuilder:
    """Строит таблицу для панели MTF."""
    
    def __init__(self, mtf_results):
        self.mtf_results = mtf_results
        self.rows = []
    
    def build_rows(self):
        """Строит строки таблицы."""
        self.rows = []
        
        for tf_name in TF_ORDER:
            if tf_name not in self.mtf_results:
                continue
            
            result = self.mtf_results[tf_name]
            wave_info = result['current_wave']
            trend = result['trend']
            
            wave_str = wave_info.get('wave', '?')
            pattern_str = wave_info.get('pattern', '?')
            direction = wave_info.get('direction', '?')
            
            if direction == 'bullish':
                dir_str = '↑ Bull'
            elif direction == 'bearish':
                dir_str = '↓ Bear'
            else:
                dir_str = '—'
            
            # Тренд (ASCII-символы — совместимы с DejaVu Sans)
            trend_str = {
                'BULLISH': '▲ BULL',
                'BEARISH': '▼ BEAR',
                'NEUTRAL': '— NEUT',
            }.get(trend, '?')
            
            self.rows.append({
                'tf': tf_name,
                'wave': wave_str,
                'pattern': pattern_str,
                'direction': dir_str,
                'trend': trend_str,
                'trend_raw': trend,
            })
        
        return self.rows
    
    def print_console(self):
        """Выводит панель в консоль."""
        if not self.rows:
            self.build_rows()
        
        print()
        print("=" * 70)
        print(" MTF ПАНЕЛЬ — Elliott Wave")
        print("=" * 70)
        print(f"{'TF':<6} {'Wave':<8} {'Pattern':<12} {'Direction':<10} {'Trend':<12}")
        print("-" * 70)
        
        for row in self.rows:
            print(f"{row['tf']:<6} {row['wave']:<8} {row['pattern']:<12} "
                  f"{row['direction']:<10} {row['trend']:<12}")
        
        print("=" * 70)
        
        if 'W1' in self.mtf_results:
            global_trend = self.mtf_results['W1']['trend']
            print(f" Глобальный тренд (W1): {global_trend}")
        print("=" * 70)
        print()
    
    def get_dataframe(self):
        if not self.rows:
            self.build_rows()
        return pd.DataFrame(self.rows)
    
    def get_summary(self):
        if not self.rows:
            self.build_rows()
        
        waves = [r['wave'] for r in self.rows]
        trends = [r['trend_raw'] for r in self.rows]
        
        return {
            'total_tf': len(self.rows),
            'waves': waves,
            'trends': trends,
            'global_trend': self.mtf_results.get('W1', {}).get('trend', 'UNKNOWN'),
        }
