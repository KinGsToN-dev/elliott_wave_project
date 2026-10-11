"""
Wyckoff Backtest - Бэктест Wyckoff + Elliott стратегий.

Запускает все стратегии (Elliott + Wyckoff) на разных символах и ТФ.
Wyckoff-стратегии анализируют df напрямую через WyckoffDetector.
Elliott-стратегии используют предварительно найденные паттерны.

Использование:
    python run_wyckoff_backtest.py
    python run_wyckoff_backtest.py --symbol EURUSD --tf H4
    python run_wyckoff_backtest.py --strategies wyckoff_spring,wyckoff_sos
    python run_wyckoff_backtest.py --only-wyckoff
"""
import sys
import os
import argparse
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
# НАСТРОЙКИ ПО УМОЛЧАНИЮ
# ============================================================
DEFAULT_SYMBOLS = ['EURUSD', 'GBPUSD', 'XAUUSD']
DEFAULT_TIMEFRAMES = ['H4', 'D1']
DEFAULT_CANDLES = 500
DEFAULT_MAX_BARS_HOLD = 50

ZIGZAG_LENGTH = 5
IMPULSE_ATR = 2.0
DIAGONAL_ATR = 1.0
CORRECTION_ATR = 1.0
USE_FILTER = True

# Названия Wyckoff-стратегий
WYCKOFF_STRATEGIES = [
    'wyckoff_spring',
    'wyckoff_sos',
    'wyckoff_utad',
    'wyckoff_sow',
    'wyckoff_combined',
]

# Названия Elliott-стратегий
ELLIOTT_STRATEGIES = [
    'w2_w3',
    'w4_w5',
    'wc_reversal',
    'w5_divergence',
    'mtf_confirmed',
    'combined',
]


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
    print(f"  [WARNING] Нет данных MT5 для {symbol} {tf_name}, использую синтетику")
    return generate_test_data(count=count)


def analyze_elliott(df):
    """Полный анализ Elliott: ZigZag + паттерны."""
    zigzag = ZigZag(df, length=ZIGZAG_LENGTH)
    pivots = zigzag.find_pivots()
    
    impulses = ImpulseDetector(pivots, df=df, min_atr_ratio=IMPULSE_ATR).find_impulses()
    diagonals = DiagonalDetector(pivots, df=df, min_atr_ratio=DIAGONAL_ATR).find_diagonals()
    corrections = CorrectionDetector(pivots, df=df, min_atr_ratio=CORRECTION_ATR).find_corrections()
    
    if USE_FILTER:
        filter_obj = OverlapFilter(impulses, diagonals, corrections)
        impulses, diagonals, corrections = filter_obj.filter()
    
    return impulses, diagonals, corrections


# MTF-цепочка: M5 -> M15 -> M30 -> H1 -> H4 -> D1 -> W1 -> (без MTF)
MTF_CHAIN = {
    'M5':  'M15',
    'M15': 'M30',
    'M30': 'H1',
    'H1':  'H4',
    'H4':  'D1',
    'D1':  'W1',
    'W1':  None,
}


def get_higher_tf_phase(symbol, current_tf):
    """
    Загружает старший ТФ и определяет его фазу.
    Цепочка: H4 -> D1 -> W1 -> None.
    """
    higher_tf = MTF_CHAIN.get(current_tf)
    if higher_tf is None:
        return None
    
    from wyckoff.detector import WyckoffDetector
    
    higher_df = load_data(symbol, higher_tf, 300)
    if higher_df is None or len(higher_df) < 50:
        return None
    
    try:
        detector = WyckoffDetector(
            range_min_bars=15,
            range_max_width_atr=5.0,
            spring_depth_atr=1.0,
            climax_volume_mult=1.5,
            phase_trend_atr_threshold=1.0,
            phase_lookback_bars=30,
        )
        result = detector.detect_all(higher_df)
        
        if result.current_phase is None:
            return 'unknown'
        
        return result.current_phase.phase.value
    except Exception:
        return None


def run_strategy(
    strategy_name,
    df,
    symbol='EURUSD',
    impulses=None,
    diagonals=None,
    corrections=None,
    higher_tf_phase=None,
):
    """Запускает одну стратегию и возвращает метрики."""
    try:
        StrategyClass = get_strategy(strategy_name)
        strategy = StrategyClass(higher_tf_phase=higher_tf_phase)
        
        # Определяем тип стратегии: Wyckoff или Elliott
        is_wyckoff = strategy_name.startswith('wyckoff_')
        
        if is_wyckoff:
            # Wyckoff-стратегии не нуждаются в impulses/diagonals/corrections
            signals = strategy.generate_signals(df, None, None, None, None)
        else:
            # Elliott-стратегии используют паттерны
            if impulses is None:
                impulses, diagonals, corrections = analyze_elliott(df)
            signals = strategy.generate_signals(
                df, impulses, diagonals, corrections, []
            )
        
        if not signals:
            return {
                'trades': 0, 'wins': 0, 'losses': 0,
                'winrate': 0, 'pf': 0, 'return': 0, 'dd': 0,
            }
        
        engine = BacktestEngine(
            max_bars_hold=DEFAULT_MAX_BARS_HOLD,
            symbol=symbol,
        )
        trades = engine.run(signals, df)
        
        if not trades:
            return {
                'trades': 0, 'wins': 0, 'losses': 0,
                'winrate': 0, 'pf': 0, 'return': 0, 'dd': 0,
            }
        
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
            'tp': m.get('tp_count', 0),
            'sl': m.get('sl_count', 0),
            'time_exit': m.get('time_count', 0),
        }
    except Exception as e:
        return {
            'trades': 0, 'wins': 0, 'losses': 0,
            'winrate': 0, 'pf': 0, 'return': 0, 'dd': 0,
            'error': str(e),
        }


def parse_args():
    """Парсинг аргументов командной строки."""
    parser = argparse.ArgumentParser(
        description='Wyckoff + Elliott Backtest',
    )
    parser.add_argument(
        '--symbol', type=str, default=None,
        help='Символ (EURUSD, GBPUSD, XAUUSD). Если не задан — все из DEFAULT_SYMBOLS.',
    )
    parser.add_argument(
        '--tf', type=str, default=None,
        help='Таймфрейм (H4, D1). Если не задан — все из DEFAULT_TIMEFRAMES.',
    )
    parser.add_argument(
        '--candles', type=int, default=DEFAULT_CANDLES,
        help=f'Количество свечей (по умолчанию {DEFAULT_CANDLES}).',
    )
    parser.add_argument(
        '--timeframes', type=str, default=None,
        help='Таймфреймы через запятую (M15,M30,H1,H4,D1). По умолчанию H4,D1.',
    )
    parser.add_argument(
        '--strategies', type=str, default=None,
        help='Список стратегий через запятую. Если не задан — все.',
    )
    parser.add_argument(
        '--only-wyckoff', action='store_true',
        help='Запускать только Wyckoff-стратегии.',
    )
    parser.add_argument(
        '--only-elliott', action='store_true',
        help='Запускать только Elliott-стратегии.',
    )
    return parser.parse_args()


def main():
    args = parse_args()
    
    # Символы
    symbols = [args.symbol] if args.symbol else DEFAULT_SYMBOLS
    
    # Таймфреймы
    if args.timeframes:
        timeframes = [tf.strip() for tf in args.timeframes.split(',')]
    elif args.tf:
        timeframes = [args.tf]
    else:
        timeframes = DEFAULT_TIMEFRAMES
    
    # Стратегии
    if args.strategies:
        strategies = [s.strip() for s in args.strategies.split(',')]
    elif args.only_wyckoff:
        strategies = WYCKOFF_STRATEGIES
    elif args.only_elliott:
        strategies = ELLIOTT_STRATEGIES
    else:
        strategies = ELLIOTT_STRATEGIES + WYCKOFF_STRATEGIES
    
    print("=" * 90)
    print(" WYCKOFF + ELLIOTT BACKTEST")
    print("=" * 90)
    print(f" Символы:      {symbols}")
    print(f" Таймфреймы:   {timeframes}")
    print(f" Свечей:       {args.candles}")
    print(f" Стратегии:    {strategies}")
    print(f" MT5 доступен: {MT5_AVAILABLE}")
    print("=" * 90)
    print()
    
    all_results = []
    
    for symbol in symbols:
        for tf_name in timeframes:
            print(f"\n{'─' * 90}")
            print(f" {symbol} | {tf_name} | {args.candles} candles")
            print(f"{'─' * 90}")
            
            # Загрузка
            df = load_data(symbol, tf_name, args.candles)
            if df is None or len(df) < 50:
                print(f"  [SKIP] Недостаточно данных ({len(df) if df is not None else 0})")
                continue
            
            print(f"  Загружено: {len(df)} свечей")
            
            # Elliott-анализ (один раз для всех Elliott-стратегий)
            impulses = diagonals = corrections = None
            has_elliott = any(not s.startswith('wyckoff_') for s in strategies)
            
            if has_elliott:
                try:
                    impulses, diagonals, corrections = analyze_elliott(df)
                    print(f"  Elliott паттерны: {len(impulses)} импульсов, "
                          f"{len(diagonals)} диагоналей, {len(corrections)} коррекций")
                except Exception as e:
                    print(f"  [WARN] Ошибка Elliott-анализа: {e}")
            
            # Запуск стратегий
            higher_tf_phase = get_higher_tf_phase(symbol, tf_name)
            if higher_tf_phase:
                print(f"  [MTF] {tf_name} -> higher TF phase = {higher_tf_phase}")
            
            for strat_name in strategies:
                result = run_strategy(
                    strat_name, df, symbol,
                    impulses, diagonals, corrections,
                    higher_tf_phase=higher_tf_phase,
                )
                
                all_results.append({
                    'symbol': symbol,
                    'tf': tf_name,
                    'strategy': strat_name,
                    'type': 'Wyckoff' if strat_name.startswith('wyckoff_') else 'Elliott',
                    'trades': result['trades'],
                    'wins': result.get('wins', 0),
                    'losses': result.get('losses', 0),
                    'winrate': result['winrate'],
                    'pf': result['pf'],
                    'return': result['return'],
                    'dd': result['dd'],
                })
                
                if result['trades'] > 0:
                    print(f"    {strat_name:20} | {result['trades']:3} trades | "
                          f"{result['winrate']*100:5.1f}% | PF {result['pf']:6.2f} | "
                          f"Ret {result['return']:+9.1f} | DD {result['dd']:8.1f}")
                else:
                    error = result.get('error', '')
                    suffix = f" (error: {error})" if error else ""
                    print(f"    {strat_name:20} | нет сигналов{suffix}")
    
    if not all_results:
        print("\n[WARN] Нет результатов")
        return
    
    # Сводная таблица
    df_results = pd.DataFrame(all_results)
    
    output_file = f'wyckoff_backtest_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'
    df_results.to_csv(output_file, index=False)
    print(f"\n[OK] Результаты сохранены: {output_file}")
    
    # Итоги по стратегиям
    print("\n" + "=" * 90)
    print(" ИТОГИ ПО СТРАТЕГИЯМ (только с trades > 0)")
    print("=" * 90)
    
    with_trades = df_results[df_results['trades'] > 0]
    
    if len(with_trades) == 0:
        print("  Нет стратегий с сигналами. Возможно, нужно больше свечей или другие параметры.")
        return
    
    summary = with_trades.groupby(['type', 'strategy']).agg({
        'trades': 'sum',
        'wins': 'sum',
        'return': 'sum',
        'winrate': 'mean',
        'pf': 'mean',
        'dd': 'mean',
    }).round(2)
    
    summary = summary.sort_values(['type', 'return'], ascending=[True, False])
    print(summary.to_string())
    
    # Сравнение Elliott vs Wyckoff
    print("\n" + "=" * 90)
    print(" СРАВНЕНИЕ ELLIOTT vs WYCKOFF")
    print("=" * 90)
    
    comparison = with_trades.groupby('type').agg({
        'trades': 'sum',
        'wins': 'sum',
        'winrate': 'mean',
        'pf': 'mean',
        'return': 'sum',
    }).round(2)
    print(comparison.to_string())
    
    # Топ-10 комбинаций
    print("\n" + "=" * 90)
    print(" ТОП-10 КОМБИНАЦИЙ (Symbol × TF × Strategy)")
    print("=" * 90)
    
    top = with_trades.nlargest(10, 'return')
    print(top[['symbol', 'tf', 'type', 'strategy', 'trades',
               'winrate', 'pf', 'return', 'dd']].to_string(index=False))
    
    print("\n[OK] Бэктест завершён!")


if __name__ == "__main__":
    main()