"""
Main - Полный анализ + бэктест.
"""
import sys
import os
import argparse

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.mt5_connector import MT5Connector, generate_test_data, MT5_AVAILABLE
from core.zigzag import ZigZag
from core.overlap_filter import OverlapFilter
from patterns.impulse import ImpulseDetector
from patterns.diagonal import DiagonalDetector
from patterns.correction import CorrectionDetector
from fib.retracement import RetracementCalculator
from fib.extension import ExtensionCalculator
from fib.clusters import ClusterFinder
from mtf.multi_timeframe import MultiTimeframeAnalyzer, TIMEFRAMES, TF_ORDER
from mtf.panel_builder import PanelBuilder
from visualization.chart_structure import StructureChart
from visualization.chart_fib import FibVisualizer
from visualization.panel import MTFPanel
from backtest.engine import BacktestEngine
from backtest.metrics import BacktestMetrics
from backtest.strategies import get_strategy, list_strategies

DEFAULT_TF = 'H4'
DEFAULT_SYMBOL = 'EURUSD'
CANDLES_COUNT = 500
ZIGZAG_LENGTH = 5
IMPULSE_ATR = 2.0
DIAGONAL_ATR = 1.0
CORRECTION_ATR = 1.0
MAX_SHOW = 5
USE_FILTER = True
SHOW_FIB = True
MAX_BARS_HOLD = 50


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tf', type=str, default=DEFAULT_TF, choices=list(TIMEFRAMES.keys()))
    parser.add_argument('--symbol', type=str, default=DEFAULT_SYMBOL)
    parser.add_argument('--candles', type=int, default=CANDLES_COUNT)
    parser.add_argument('--zigzag', type=int, default=ZIGZAG_LENGTH)
    parser.add_argument('--show', type=int, default=MAX_SHOW)
    parser.add_argument('--no-filter', action='store_true')
    parser.add_argument('--no-fib', action='store_true')
    parser.add_argument('--mtf', action='store_true')
    parser.add_argument('--backtest', action='store_true', help='Запустить бэктест')
    parser.add_argument('--strategy', type=str, default=None, help='Имя стратегии (например, w2_w3)')
    parser.add_argument('--all-strategies', action='store_true', help='Запустить все стратегии')
    parser.add_argument('--max-bars', type=int, default=MAX_BARS_HOLD, help='Макс свечей удержания')
    return parser.parse_args()


def load_data_for_tf(symbol, tf_name, count):
    tf_value = TIMEFRAMES.get(tf_name, 16388)
    if MT5_AVAILABLE:
        connector = MT5Connector(symbol=symbol, timeframe=tf_value)
        if connector.connect():
            df = connector.get_candles(count=count)
            connector.disconnect()
            if df is not None and len(df) > 20:
                return df
    return generate_test_data(count=count)


def analyze_symbol(df, zigzag_length, use_filter, impulse_atr, diagonal_atr, correction_atr):
    """Полный анализ: ZigZag + паттерны."""
    zigzag = ZigZag(df, length=zigzag_length)
    pivots = zigzag.find_pivots()
    
    impulses = ImpulseDetector(pivots, df=df, min_atr_ratio=impulse_atr).find_impulses()
    diagonals = DiagonalDetector(pivots, df=df, min_atr_ratio=diagonal_atr).find_diagonals()
    corrections = CorrectionDetector(pivots, df=df, min_atr_ratio=correction_atr).find_corrections()
    
    if use_filter:
        filter_obj = OverlapFilter(impulses, diagonals, corrections)
        impulses, diagonals, corrections = filter_obj.filter()
    
    return pivots, impulses, diagonals, corrections


def run_backtest(args):
    """Бэктест одной или всех стратегий."""
    tf_name = args.tf
    tf_value = TIMEFRAMES[tf_name]
    
    print("=" * 60)
    print(f" BACKTEST — {args.symbol} {tf_name} — {args.candles} candles")
    print("=" * 60)
    
    # Загрузка данных
    df = None
    if MT5_AVAILABLE:
        connector = MT5Connector(symbol=args.symbol, timeframe=tf_value)
        if connector.connect():
            df = connector.get_candles(count=args.candles)
            connector.disconnect()
    if df is None:
        df = generate_test_data(count=args.candles)
    
    print(f"[OK] Загружено {len(df)} свечей.")
    
    # Анализ
    pivots, impulses, diagonals, corrections = analyze_symbol(
        df, args.zigzag, USE_FILTER, IMPULSE_ATR, DIAGONAL_ATR, CORRECTION_ATR
    )
    
    print(f"[OK] Импульсов: {len(impulses)}, Диагоналей: {len(diagonals)}, Коррекций: {len(corrections)}")
    
    # Выбор стратегий
    if args.all_strategies:
        strategies_to_run = list_strategies()
    elif args.strategy:
        strategies_to_run = [s.strip() for s in args.strategy.split(',')]
    else:
        strategies_to_run = ['w2_w3']
    
    print(f"\n[INFO] Запуск стратегий: {strategies_to_run}")
    
    # Результаты
    all_results = {}
    
    for strat_name in strategies_to_run:
        try:
            StrategyClass = get_strategy(strat_name)
            strategy = StrategyClass()
            
            # Генерация сигналов
            signals = strategy.generate_signals(df, impulses, diagonals, corrections, [])
            
            if not signals:
                print(f"\n[{strat_name}] Нет сигналов.")
                all_results[strat_name] = {'total_trades': 0, 'winrate': 0, 'profit_factor': 0}
                continue
            
            # Симуляция
            engine = BacktestEngine(max_bars_hold=args.max_bars)
            trades = engine.run(signals, df)
            
            # Метрики
            metrics = BacktestMetrics(trades)
            m = metrics.print_summary(strategy.name)
            all_results[strat_name] = m
        except Exception as e:
            print(f"\n[{strat_name}] ОШИБКА: {e}")
            all_results[strat_name] = {'total_trades': 0, 'error': str(e)}
    
    # Сравнительная таблица
    if len(all_results) > 1:
        print()
        print("=" * 70)
        print(" СРАВНЕНИЕ СТРАТЕГИЙ")
        print("=" * 70)
        print(f"{'Strategy':<15} {'Trades':<8} {'Winrate':<10} {'PF':<8} {'Return':<10}")
        print("-" * 70)
        for name, m in all_results.items():
            if m.get('total_trades', 0) > 0:
                print(f"{name:<15} {m['total_trades']:<8} "
                      f"{m['winrate']*100:>6.1f}%   "
                      f"{m['profit_factor']:>5.2f}   "
                      f"{m['total_return']:>+7.1f} pips")
        print("=" * 70)
        print()


def run_single_tf(args, tf_name):
    """Анализ одного ТФ + график."""
    print("=" * 60)
    print(f" Elliott Wave Full Analysis")
    print(f" {args.symbol} | {tf_name} | {args.candles} candles")
    print("=" * 60)
    
    tf_value = TIMEFRAMES[tf_name]
    
    df = None
    if MT5_AVAILABLE:
        connector = MT5Connector(symbol=args.symbol, timeframe=tf_value)
        if connector.connect():
            df = connector.get_candles(count=args.candles)
            connector.disconnect()
    if df is None:
        df = generate_test_data(count=args.candles)
    
    print(f"\n[INFO] Загружено {len(df)} свечей.")
    
    pivots, impulses, diagonals, corrections = analyze_symbol(
        df, args.zigzag, USE_FILTER and not args.no_filter,
        IMPULSE_ATR, DIAGONAL_ATR, CORRECTION_ATR
    )
    
    print(f"\n{'='*60}")
    print(f" ПАТТЕРНЫ {'(после фильтра)' if USE_FILTER and not args.no_filter else ''}")
    print(f"{'='*60}")
    print(f" Импульсов:    {len(impulses)}")
    print(f" Диагоналей:   {len(diagonals)}")
    print(f" Коррекций:    {len(corrections)}")
    
    fib_results = []
    clusters = []
    
    if SHOW_FIB and not args.no_fib and impulses:
        print(f"\n{'='*60}")
        print(f" ФИБОНАЧЧИ")
        print(f"{'='*60}")
        
        retr = RetracementCalculator()
        ext = ExtensionCalculator()
        
        last_imp = impulses[-1]
        retr_results = retr.calculate_all([last_imp], [])
        ext_results = ext.calculate_all([last_imp], [])
        
        for r in retr_results:
            for key in ['w2', 'w4', 'wb']:
                if key in r and r[key] is not None:
                    fib_results.append(r[key])
        for r in ext_results:
            for key in ['w3', 'w5', 'wc']:
                if key in r and r[key] is not None:
                    fib_results.append(r[key])
        
        cluster_finder = ClusterFinder(tolerance_pct=0.003)
        clusters = cluster_finder.find_clusters(fib_results)
    
    print(f"\n[INFO] Построение графика...")
    chart = StructureChart(title=f"{args.symbol} {tf_name} - EW + Fibonacci")
    chart.show(
        df=df, pivots=pivots, impulses=impulses,
        diagonals=diagonals, corrections=corrections,
        max_show=args.show,
        fib_results=fib_results if SHOW_FIB and not args.no_fib else None,
        clusters=clusters if SHOW_FIB and not args.no_fib else None,
    )
    chart.save(f'structure_{args.symbol}_{tf_name}.png')
    print("\n[OK] Готово!")


def run_mtf(args):
    """MTF-анализ."""
    print("=" * 60)
    print(f" MTF Analysis — все 5 таймфреймов")
    print(f" {args.symbol} | {args.candles} candles per TF")
    print("=" * 60)
    
    mtf = MultiTimeframeAnalyzer(symbol=args.symbol, candles_count=args.candles)
    
    def loader(tf_name, count):
        return load_data_for_tf(args.symbol, tf_name, count)
    
    results = mtf.analyze_all(loader)
    
    if not results:
        print("[ERROR] Не удалось проанализировать ни один ТФ")
        return
    
    pb = PanelBuilder(results)
    rows = pb.build_rows()
    pb.print_console()
    
    summary = pb.get_summary()
    panel = MTFPanel(rows, global_trend=summary['global_trend'])
    panel.show()
    panel.save('mtf_panel.png')
    
    print("\n[OK] MTF-анализ завершён!")


def main():
    args = parse_args()
    
    if args.backtest:
        run_backtest(args)
    elif args.mtf:
        run_mtf(args)
    else:
        run_single_tf(args, args.tf)


if __name__ == "__main__":
    main()
