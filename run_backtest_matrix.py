"""
Backtest Matrix - Мульти-символьный и мульти-ТФ бэктест.

Запускает все стратегии на разных символах и таймфреймах.
Собирает результаты в сводную таблицу.
"""
import sys
import os
import pandas as pd
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.mt5_connector import MT5Connector, generate_test_data, MT5_AVAILABLE
from core.zigzag import ZigZag
from core.overlap_filter import OverlapFilter
from patterns.impulse import ImpulseDetector
from patterns.diagonal import DiagonalDetector
from patterns.correction import CorrectionDetector
from backtest.engine import BacktestEngine
from backtest.metrics import BacktestMetrics
from backtest.strategies import get_strategy, list_strategies
from mtf.multi_timeframe import TIMEFRAMES


# ============================================================
# НАСТРОЙКИ
# ============================================================
SYMBOLS = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD']
TIMEFRAMES_TO_TEST = ['H4', 'D1']
CANDLES = 2000
ZIGZAG_LENGTH = 5
IMPULSE_ATR = 2.0
DIAGONAL_ATR = 1.0
CORRECTION_ATR = 1.0
MAX_BARS_HOLD = 50
USE_FILTER = True


def load_data(symbol, tf_name, count):
    """Загрузка данных для символа и ТФ."""
    tf_value = TIMEFRAMES.get(tf_name, 16388)
    
    if MT5_AVAILABLE:
        connector = MT5Connector(symbol=symbol, timeframe=tf_value)
        if connector.connect():
            df = connector.get_candles(count=count)
            connector.disconnect()
            if df is not None and len(df) > 20:
                return df
    
    # Fallback
    print(f"  [WARNING] Нет данных MT5 для {symbol} {tf_name}, использую тестовые")
    return generate_test_data(count=count)


def analyze(df):
    """Полный анализ: ZigZag + паттерны."""
    zigzag = ZigZag(df, length=ZIGZAG_LENGTH)
    pivots = zigzag.find_pivots()
    
    impulses = ImpulseDetector(pivots, df=df, min_atr_ratio=IMPULSE_ATR).find_impulses()
    diagonals = DiagonalDetector(pivots, df=df, min_atr_ratio=DIAGONAL_ATR).find_diagonals()
    corrections = CorrectionDetector(pivots, df=df, min_atr_ratio=CORRECTION_ATR).find_corrections()
    
    if USE_FILTER:
        filter_obj = OverlapFilter(impulses, diagonals, corrections)
        impulses, diagonals, corrections = filter_obj.filter()
    
    return impulses, diagonals, corrections


def run_strategy(strategy_name, df, impulses, diagonals, corrections, symbol='EURUSD'):
    """Запускает одну стратегию и возвращает метрики."""
    try:
        StrategyClass = get_strategy(strategy_name)
        strategy = StrategyClass()
        
        signals = strategy.generate_signals(df, impulses, diagonals, corrections, [])
        
        if not signals:
            return {
                'trades': 0, 'wins': 0, 'losses': 0,
                'winrate': 0, 'pf': 0, 'return': 0, 'dd': 0,
            }
        
        engine = BacktestEngine(max_bars_hold=MAX_BARS_HOLD, symbol=symbol)
        trades = engine.run(signals, df)
        
        metrics = BacktestMetrics(trades)
        m = metrics.calculate()
        
        return {
            'trades': m['total_trades'],
            'wins': m['wins'],
            'losses': m['losses'],
            'winrate': m['winrate'],
            'pf': m['profit_factor'],
            'return': m['total_return'],
            'dd': m['max_drawdown'],
        }
    except Exception as e:
        return {
            'trades': 0, 'wins': 0, 'losses': 0,
            'winrate': 0, 'pf': 0, 'return': 0, 'dd': 0,
            'error': str(e),
        }


def main():
    print("=" * 80)
    print(" BACKTEST MATRIX — Multi-Symbol × Multi-Timeframe")
    print("=" * 80)
    print(f" Символы:      {SYMBOLS}")
    print(f" Таймфреймы:   {TIMEFRAMES_TO_TEST}")
    print(f" Свечей:       {CANDLES}")
    print(f" Стратегии:    {list_strategies()}")
    print("=" * 80)
    print()
    
    all_results = []
    
    for symbol in SYMBOLS:
        for tf_name in TIMEFRAMES_TO_TEST:
            print(f"\n{'─' * 80}")
            print(f" {symbol} | {tf_name} | {CANDLES} candles")
            print(f"{'─' * 80}")
            
            # Загрузка данных
            df = load_data(symbol, tf_name, CANDLES)
            if df is None or len(df) < 20:
                print(f"  [SKIP] Нет данных")
                continue
            
            print(f"  Загружено: {len(df)} свечей")
            
            # Анализ
            impulses, diagonals, corrections = analyze(df)
            print(f"  Паттерны: {len(impulses)} импульсов, {len(diagonals)} диагоналей, {len(corrections)} коррекций")
            
            # Запуск всех стратегий
            for strat_name in list_strategies():
                result = run_strategy(strat_name, df, impulses, diagonals, corrections, symbol=symbol)
                
                all_results.append({
                    'symbol': symbol,
                    'tf': tf_name,
                    'strategy': strat_name,
                    'trades': result['trades'],
                    'wins': result['wins'],
                    'losses': result['losses'],
                    'winrate': result['winrate'],
                    'pf': result['pf'],
                    'return': result['return'],
                    'dd': result['dd'],
                })
                
                if result['trades'] > 0:
                    print(f"    {strat_name:15} | {result['trades']:3} trades | "
                          f"{result['winrate']*100:5.1f}% | PF {result['pf']:6.2f} | "
                          f"Ret {result['return']:+8.1f} | DD {result['dd']:7.1f}")
                else:
                    print(f"    {strat_name:15} | нет сигналов")
    
    # Итоговая таблица
    print()
    print("=" * 80)
    print(" СВОДНАЯ ТАБЛИЦА")
    print("=" * 80)
    
    df_results = pd.DataFrame(all_results)
    
    # Сохраняем в CSV
    output_file = f'backtest_matrix_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'
    df_results.to_csv(output_file, index=False)
    print(f"\n[OK] Результаты сохранены в: {output_file}")
    
    # Группировка по стратегиям
    print("\n" + "=" * 80)
    print(" СРЕДНИЙ WINRATE ПО СТРАТЕГИЯМ")
    print("=" * 80)
    
    summary = df_results[df_results['trades'] > 0].groupby('strategy').agg({
        'trades': 'sum',
        'wins': 'sum',
        'return': 'sum',
        'winrate': 'mean',
        'pf': 'mean',
    }).round(2)
    
    summary = summary.sort_values('return', ascending=False)
    print(summary.to_string())
    
    print("\n" + "=" * 80)
    print(" ЛУЧШИЕ КОМБИНАЦИИ (Символ × ТФ × Стратегия)")
    print("=" * 80)
    
    top = df_results[df_results['trades'] > 0].nlargest(10, 'return')
    print(top[['symbol', 'tf', 'strategy', 'trades', 'winrate', 'pf', 'return', 'dd']].to_string(index=False))
    
    print("\n[OK] Бэктест-матрица завершена!")


if __name__ == "__main__":
    main()
