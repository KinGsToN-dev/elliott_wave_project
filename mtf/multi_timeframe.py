"""
MultiTimeframe - Загрузка и анализ 5 таймфреймов.

Таймфреймы:
- M15, H1, H4, D1, W1.
"""
import pandas as pd
import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.zigzag import ZigZag
from core.overlap_filter import OverlapFilter
from patterns.impulse import ImpulseDetector
from patterns.diagonal import DiagonalDetector
from patterns.correction import CorrectionDetector


# Маппинг таймфреймов MT5
TIMEFRAMES = {
    'M15': 15,
    'H1': 16385,
    'H4': 16388,
    'D1': 16408,
    'W1': 32769,
}

# Порядок от младшего к старшему
TF_ORDER = ['M15', 'H1', 'H4', 'D1', 'W1']


class MultiTimeframeAnalyzer:
    """Анализ 5 таймфреймов."""
    
    def __init__(self, symbol='EURUSD', candles_count=500):
        self.symbol = symbol
        self.candles_count = candles_count
        self.results = {}  # tf_name → dict с анализом
    
    def analyze_tf(self, df, tf_name, zigzag_length=5,
                   impulse_atr=2.0, diagonal_atr=1.0, correction_atr=1.0):
        """
        Анализ одного таймфрейма.
        
        Args:
            df: DataFrame со свечами
            tf_name: 'M15', 'H1', etc.
            zigzag_length: длина ZigZag
            impulse_atr, diagonal_atr, correction_atr: ATR-фильтры
        
        Returns:
            dict с результатами анализа
        """
        if df is None or len(df) < 20:
            return None
        
        # ZigZag
        zigzag = ZigZag(df, length=zigzag_length)
        pivots = zigzag.find_pivots()
        
        # Паттерны
        impulses = ImpulseDetector(pivots, df=df, min_atr_ratio=impulse_atr).find_impulses()
        diagonals = DiagonalDetector(pivots, df=df, min_atr_ratio=diagonal_atr).find_diagonals()
        corrections = CorrectionDetector(pivots, df=df, min_atr_ratio=correction_atr).find_corrections()
        
        # Фильтр наложений
        filter_obj = OverlapFilter(impulses, diagonals, corrections)
        impulses, diagonals, corrections = filter_obj.filter()
        
        # Текущая волна
        current_wave = self._determine_current_wave(impulses, diagonals, corrections, df)
        
        # Глобальный тренд (EMA 200)
        trend = self._determine_trend(df)
        
        return {
            'tf': tf_name,
            'candles': len(df),
            'impulses': impulses,
            'diagonals': diagonals,
            'corrections': corrections,
            'current_wave': current_wave,
            'trend': trend,
        }
    
    def _determine_current_wave(self, impulses, diagonals, corrections, df):
        """
        Определяет текущую волну — в какой волне мы находимся сейчас.
        
        Логика:
        1. Если последний паттерн — импульс, смотрим на последнюю точку.
        2. Если точка = (5) — импульс завершён.
        3. Если в импульсе не хватает точек — мы внутри волны.
        """
        if not impulses and not diagonals and not corrections:
            return {'wave': '?', 'pattern': 'unknown', 'position': 'unknown'}
        
        # Берём последний паттерн по времени
        all_patterns = []
        for imp in impulses:
            all_patterns.append({
                'end_time': imp['end_time'],
                'type': 'impulse',
                'direction': imp['direction'],
                'points': imp['points'],
                'size': imp['size'],
            })
        for d in diagonals:
            all_patterns.append({
                'end_time': d['end_time'],
                'type': 'diagonal',
                'direction': d['direction'],
                'points': d['points'],
                'size': d['size'],
            })
        for c in corrections:
            all_patterns.append({
                'end_time': c['end_time'],
                'type': c['type'],
                'direction': c['direction'],
                'points': c['points'],
                'size': c['size'],
            })
        
        if not all_patterns:
            return {'wave': '?', 'pattern': 'unknown', 'position': 'unknown'}
        
        # Сортируем по времени окончания
        last_pattern = max(all_patterns, key=lambda x: x['end_time'])
        
        # Определяем последнюю волну
        points = last_pattern['points']
        last_label = points[-1][2] if points else '?'
        
        # Если последняя точка — конец импульса (5)
        if last_pattern['type'] == 'impulse' and last_label == '5':
            return {
                'wave': '(5)',
                'pattern': 'impulse',
                'position': 'completed',
                'direction': last_pattern['direction'],
            }
        
        # Если паттерн — коррекция (A/B/C)
        if last_pattern['type'] in ['zigzag', 'flat', 'triangle']:
            return {
                'wave': f'({last_label})',
                'pattern': last_pattern['type'],
                'position': 'in_progress',
                'direction': last_pattern['direction'],
            }
        
        # Общий случай
        return {
            'wave': f'({last_label})',
            'pattern': last_pattern['type'],
            'position': 'in_progress',
            'direction': last_pattern.get('direction', '?'),
        }
    
    def _determine_trend(self, df):
        """Определяет тренд по EMA 200."""
        if df is None or len(df) < 200:
            ema_len = min(len(df), 50)
        else:
            ema_len = 200
        
        ema = df['close'].ewm(span=ema_len, adjust=False).mean()
        current_price = df['close'].iloc[-1]
        current_ema = ema.iloc[-1]
        
        if current_price > current_ema:
            return 'BULLISH'
        elif current_price < current_ema:
            return 'BEARISH'
        return 'NEUTRAL'
    
    def get_global_trend(self):
        """Определяет глобальный тренд по W1."""
        if 'W1' in self.results:
            return self.results['W1']['trend']
        return 'UNKNOWN'
    
    def analyze_all(self, data_loader_func):
        """
        Анализ всех 5 ТФ.
        
        Args:
            data_loader_func: функция, которая принимает (tf_name, count) и возвращает df
        
        Returns:
            dict {tf_name: analysis_result}
        """
        print(f"\n[INFO] Анализ {len(TF_ORDER)} таймфреймов...")
        
        for tf_name in TF_ORDER:
            print(f"\n[INFO] Обработка {tf_name}...")
            try:
                df = data_loader_func(tf_name, self.candles_count)
                if df is None or len(df) < 20:
                    print(f"  [SKIP] Недостаточно данных для {tf_name}")
                    continue
                
                # Разные параметры ZigZag для разных ТФ
                zigzag_len = self._get_zigzag_length(tf_name)
                
                result = self.analyze_tf(df, tf_name, zigzag_length=zigzag_len)
                if result:
                    self.results[tf_name] = result
                    wave = result['current_wave']['wave']
                    trend = result['trend']
                    print(f"  [OK] {tf_name}: волна {wave}, тренд {trend}")
            except Exception as e:
                print(f"  [ERROR] {tf_name}: {e}")
        
        print(f"\n[OK] Проанализировано ТФ: {len(self.results)}")
        return self.results
    
    def _get_zigzag_length(self, tf_name):
        """Возвращает длину ZigZag для таймфрейма."""
        mapping = {
            'M15': 3,
            'H1': 5,
            'H4': 5,
            'D1': 5,
            'W1': 3,
        }
        return mapping.get(tf_name, 5)
    
    def get_results(self):
        return self.results
