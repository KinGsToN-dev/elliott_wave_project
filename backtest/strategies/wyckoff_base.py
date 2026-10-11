"""
WyckoffBaseStrategy - базовый класс для Wyckoff-стратегий.

Использует WyckoffDetector для анализа df.
Совместим с BaseStrategy (принимает impulses, diagonals, ... но игнорирует их).
"""
import pandas as pd
import numpy as np
from datetime import datetime

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from .base import BaseStrategy
from wyckoff.detector import WyckoffDetector
from wyckoff.phases import Phase


class WyckoffBaseStrategy(BaseStrategy):
    """
    Базовый класс для Wyckoff-стратегий.
    
    Все наследники переопределяют:
    - should_enter(analysis, idx, df) -> Optional[dict]
    - _get_entry_price(analysis, idx, df) -> float
    - _get_stop(analysis, idx, df, direction) -> float
    - _get_target(analysis, idx, df, direction, entry, stop) -> float
    """
    
    def __init__(
        self,
        name: str = "Wyckoff Base",
        target_atr_mult: float = 2.0,
        stop_atr_mult: float = 0.5,
        min_confidence: float = 0.4,
    ):
        super().__init__(name=name)
        self.description = "Wyckoff strategy base"
        self.target_atr_mult = target_atr_mult
        self.stop_atr_mult = stop_atr_mult
        self.min_confidence = min_confidence
        self.detector = WyckoffDetector()
    
    def _compute_atr(self, df: pd.DataFrame) -> pd.Series:
        """ATR для расчёта таргетов."""
        high = df['high']
        low = df['low']
        close = df['close']
        prev_close = close.shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ], axis=1).max(axis=1)
        return tr.rolling(window=14, min_periods=1).mean()
    
    def should_enter(self, analysis, idx: int, df: pd.DataFrame):
        """
        Проверяет, есть ли сигнал на баре idx.
        
        Переопределяется в наследниках.
        Возвращает dict с сигналом или None.
        """
        return None
    
    def _get_entry_price(
        self,
        analysis,
        idx: int,
        df: pd.DataFrame,
    ) -> float:
        """Цена входа."""
        return float(df.iloc[idx]['close'])
    
    def _get_stop(
        self,
        analysis,
        idx: int,
        df: pd.DataFrame,
        direction: str,
    ) -> float:
        """Цена стопа."""
        atr = self._compute_atr(df)
        cur_atr = float(atr.iloc[idx])
        price = float(df.iloc[idx]['close'])
        
        if direction == 'BUY':
            return price - cur_atr * self.stop_atr_mult
        else:
            return price + cur_atr * self.stop_atr_mult
    
    def _get_target(
        self,
        analysis,
        idx: int,
        df: pd.DataFrame,
        direction: str,
        entry: float,
        stop: float,
    ) -> float:
        """
        Цена цели.
        
        Использует ATR-множитель.
        """
        atr = self._compute_atr(df)
        cur_atr = float(atr.iloc[idx])
        
        if direction == 'BUY':
            return entry + cur_atr * self.target_atr_mult
        else:
            return entry - cur_atr * self.target_atr_mult
    
    def generate_signals(
        self,
        df: pd.DataFrame,
        impulses=None,
        diagonals=None,
        corrections=None,
        combinations=None,
    ):
        """
        Генерирует сигналы Wyckoff.
        
        impulses/diagonals/corrections/combinations игнорируются
        (они для Elliott-стратегий).
        """
        trades = []
        
        if df is None or len(df) < 50:
            return trades
        
        # Прогоняем анализ на окне от 50 баров и далее
        # (чтобы не гонять детектор на каждый бар)
        step = 5  # каждые 5 баров
        for idx in range(50, len(df) - 1, step):
            window = df.iloc[:idx + 1]
            
            try:
                analysis = self.detector.detect_all(window)
            except Exception:
                continue
            
            # Проверяем сигнал
            try:
                signal = self.should_enter(analysis, idx, df)
            except Exception:
                continue
            
            if signal is None:
                continue
            
            direction = signal.get('direction', 'BUY')
            entry_price = signal.get('entry_price', df.iloc[idx]['close'])
            
            stop = self._get_stop(analysis, idx, df, direction)
            target = self._get_target(
                analysis, idx, df, direction, entry_price, stop
            )
            
            # Проверка R:R >= 2
            risk = abs(entry_price - stop)
            reward = abs(target - entry_price)
            if risk <= 0 or reward / risk < 1.5:
                continue
            
            trades.append({
                'entry_time': df.index[idx],
                'entry_price': float(entry_price),
                'direction': direction,
                'target': float(target),
                'stop': float(stop),
                'pattern': signal.get('pattern', self.name),
                'confidence': signal.get('confidence', 0.5),
                'phase': (
                    analysis.current_phase.phase.value
                    if analysis.current_phase else 'unknown'
                ),
            })
        
        return trades
    
    def _find_event_by_type(self, analysis, event_type: str):
        """Ищет событие по типу."""
        for e in analysis.events:
            if e.type == event_type:
                return e
        return None