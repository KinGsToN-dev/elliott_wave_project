"""
Monitor - Мониторинг рынка в реальном времени.
"""
import sys
import os
import time
import pandas as pd
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.mt5_connector import MT5Connector, MT5_AVAILABLE
from core.zigzag import ZigZag
from core.overlap_filter import OverlapFilter
from core.mode_loader import get_mode
from core.mtf_filter import MTFFilter
from patterns.impulse import ImpulseDetector
from patterns.diagonal import DiagonalDetector
from patterns.correction import CorrectionDetector
from mtf.multi_timeframe import TIMEFRAMES
from backtest.strategies import get_strategy
from live.state import SignalState


class MarketMonitor:
    """Мониторинг рынка в реальном времени."""
    
    def __init__(self, symbol='EURUSD', mode='intraday', strategies=None,
                 candles=500, interval=300, max_age_hours=168):
        self.symbol = symbol
        self.mode_name = mode
        self.mode = get_mode(mode)
        self.candles = candles
        self.interval = interval
        self.max_age_hours = max_age_hours
        
        if strategies is None:
            self.strategies = self.mode.get('strategies', ['combined'])
        else:
            self.strategies = strategies
        
        self.tf_name = self.mode['timeframes'][0]
        self.tf_value = TIMEFRAMES.get(self.tf_name, 16388)
        
        self.state = SignalState()
        self.journal = []
        
        print(f"[INIT] Monitor: {symbol} | {mode} | {self.tf_name}")
        print(f"[INIT] Стратегии: {self.strategies}")
        print(f"[INIT] Интервал: {interval} сек")
        print(f"[INIT] Max age: {max_age_hours} ч")
    
    def load_data(self):
        if not MT5_AVAILABLE:
            return None
        
        connector = MT5Connector(symbol=self.symbol, timeframe=self.tf_value)
        if not connector.connect():
            return None
        
        df = connector.get_candles(count=self.candles)
        connector.disconnect()
        return df
    
    def analyze(self, df):
        zigzag_len = self.mode['zigzag_length']
        impulse_atr = self.mode['impulse_atr']
        diagonal_atr = self.mode['diagonal_atr']
        correction_atr = self.mode['correction_atr']
        
        zigzag = ZigZag(df, length=zigzag_len)
        pivots = zigzag.find_pivots()
        
        impulses = ImpulseDetector(pivots, df=df, min_atr_ratio=impulse_atr).find_impulses()
        diagonals = DiagonalDetector(pivots, df=df, min_atr_ratio=diagonal_atr).find_diagonals()
        corrections = CorrectionDetector(pivots, df=df, min_atr_ratio=correction_atr).find_corrections()
        
        filter_obj = OverlapFilter(impulses, diagonals, corrections)
        impulses, diagonals, corrections = filter_obj.filter()
        
        return pivots, impulses, diagonals, corrections
    
    def generate_signals(self, df, impulses, diagonals, corrections):
        all_signals = []
        
        mtf_filter = None
        if self.mode.get('use_mtf_filter'):
            mtf_tf = self.mode.get('mtf_timeframe', 'H4')
            mtf_value = TIMEFRAMES.get(mtf_tf, 16388)
            
            connector = MT5Connector(symbol=self.symbol, timeframe=mtf_value)
            if connector.connect():
                mtf_data = connector.get_candles(count=self.candles)
                connector.disconnect()
                
                if mtf_data is not None:
                    mtf_filter = MTFFilter(mtf_timeframe=mtf_tf)
                    mtf_filter.update_trend(mtf_data)
        
        for strat_name in self.strategies:
            try:
                StrategyClass = get_strategy(strat_name)
                strategy = StrategyClass()
                
                signals = strategy.generate_signals(df, impulses, diagonals, corrections, [])
                
                if mtf_filter:
                    signals = mtf_filter.filter_signals(signals)
                
                for sig in signals:
                    sig['strategy'] = strat_name
                    sig['symbol'] = self.symbol
                    sig['mode'] = self.mode_name
                
                all_signals.extend(signals)
            except Exception as e:
                print(f"[ERROR] Стратегия {strat_name}: {e}")
        
        return all_signals
    
    def is_signal_actual(self, signal, df):
        entry_time = signal.get('entry_time')
        target = signal.get('target')
        stop = signal.get('stop')
        direction = signal.get('direction')
        
        if not all([entry_time, target, stop, direction]):
            return True
        
        try:
            after = df.loc[df.index > pd.to_datetime(entry_time)]
        except Exception:
            return True
        
        if len(after) == 0:
            return True
        
        for _, row in after.iterrows():
            high = row['high']
            low = row['low']
            
            if direction == 'BUY':
                if high >= target:
                    return False
                if low <= stop:
                    return False
            else:
                if low <= target:
                    return False
                if high >= stop:
                    return False
        
        return True
    
    def update_active_signals(self, df):
        """
        Обновляет статусы активных сигналов.
        Проверяет только СВЕЖИЕ бары (после created_at).
        """
        active = self.state.get_active()
        
        if not active:
            return 0
        
        updated = 0
        
        for sig in active:
            entry_time = sig.get('entry_time')
            created_at = sig.get('created_at')
            target = sig.get('target')
            stop = sig.get('stop')
            direction = sig.get('direction')
            sid = sig.get('id')
            
            if not all([entry_time, created_at, target, stop, direction]):
                continue
            
            # Проверяем только бары ПОСЛЕ создания сигнала
            try:
                created_dt = pd.to_datetime(created_at)
                after = df.loc[df.index > created_dt]
            except Exception:
                continue
            
            if len(after) == 0:
                continue
            
            for _, row in after.iterrows():
                high = row['high']
                low = row['low']
                
                if direction == 'BUY':
                    if high >= target:
                        self.state.update_status(sid, 'TARGET_HIT')
                        updated += 1
                        break
                    if low <= stop:
                        self.state.update_status(sid, 'STOP_HIT')
                        updated += 1
                        break
                else:
                    if low <= target:
                        self.state.update_status(sid, 'TARGET_HIT')
                        updated += 1
                        break
                    if high >= stop:
                        self.state.update_status(sid, 'STOP_HIT')
                        updated += 1
                        break
        
        return updated
    
    def is_new_signal(self, signal):
        sid = self.state._make_id(signal)
        return sid not in self.state.state
    
    def run_once(self):
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Проверка рынка...")
        
        df = self.load_data()
        if df is None or len(df) < 20:
            print("[WARN] Недостаточно данных")
            return []
        
        # Обновляем статусы активных
        updated = self.update_active_signals(df)
        if updated > 0:
            print(f"[INFO] Обновлено статусов: {updated}")
        
        pivots, impulses, diagonals, corrections = self.analyze(df)
        print(f"[INFO] Паттерны: {len(impulses)} импульсов, {len(diagonals)} диагоналей, {len(corrections)} коррекций")
        
        signals = self.generate_signals(df, impulses, diagonals, corrections)
        print(f"[INFO] Всего сигналов: {len(signals)}")
        
        actual_signals = [s for s in signals if self.is_signal_actual(s, df)]
        print(f"[INFO] Актуальных: {len(actual_signals)}")
        
        new_signals = [s for s in actual_signals if self.is_new_signal(s)]
        
        if not hasattr(self, '_first_run_done'):
            self._first_run_done = True
            if len(new_signals) > 3:
                print(f"[INFO] Первый запуск: {len(new_signals)} сигналов -> только 3 последних")
                new_signals = new_signals[-3:]
        
        cutoff = datetime.now() - timedelta(hours=self.max_age_hours)
        
        fresh_signals = []
        for sig in new_signals:
            entry_time = sig.get('entry_time')
            if entry_time is None:
                continue
            try:
                if hasattr(entry_time, 'to_pydatetime'):
                    entry_dt = entry_time.to_pydatetime()
                else:
                    entry_dt = entry_time
                
                if entry_dt > cutoff:
                    fresh_signals.append(sig)
            except Exception:
                continue
        
        print(f"[INFO] Свежих сигналов (< {self.max_age_hours}ч): {len(fresh_signals)}")
        new_signals = fresh_signals
        
        print(f"[INFO] Новых сигналов: {len(new_signals)}")
        
        for sig in new_signals:
            self.state.add(sig)
        
        for sig in new_signals:
            self.journal.append(sig)
        
        return new_signals
    
    def run(self, max_iterations=None):
        print(f"\n{'=' * 60}")
        print(f" LIVE MONITOR ЗАПУЩЕН")
        print(f" {self.symbol} | {self.mode_name} | {self.tf_name}")
        print(f" Интервал: {self.interval} сек")
        print(f"{'=' * 60}\n")
        
        iteration = 0
        
        try:
            while True:
                iteration += 1
                new_signals = self.run_once()
                
                if new_signals:
                    yield new_signals
                
                if max_iterations and iteration >= max_iterations:
                    break
                
                print(f"[INFO] Ожидание {self.interval} сек...")
                time.sleep(self.interval)
        
        except KeyboardInterrupt:
            print(f"\n[INFO] Остановлено пользователем")
            print(f"[INFO] Всего сигналов: {len(self.journal)}")
        
        return self.journal