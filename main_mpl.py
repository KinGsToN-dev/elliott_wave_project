"""
Main - Полный анализ + бэктест + режимы.
"""
import sys
import os
import argparse

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.mt5_connector import MT5Connector, generate_test_data, MT5_AVAILABLE
from core.zigzag import ZigZag
from core.overlap_filter import OverlapFilter
from core.mode_loader import get_mode, list_modes
from core.mtf_filter import MTFFilter
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
CANDLES_COUNT = 1000
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
    parser.add_argument('--backtest', action='store_true')
    parser.add_argument('--strategy', type=str, default=None)
    parser.add_argument('--all-strategies', action='store_true')
    parser.add_argument('--max-bars', type=int, default=MAX_BARS_HOLD)
    parser.add_argument('--mode', type=str, default=None, choices=list_modes(),
                       help='Режим торговли (swing, position, intraday)')
    parser.add_argument('--live', action='store_true',
                       help='Запустить Live-режим')
    parser.add_argument('--interval', type=int, default=300,
                       help='Интервал проверки в Live-режиме (сек)')
    parser.add_argument('--symbols', type=str, default=None,
                       help='Символы через запятую (EURUSD,GBPUSD,XAUUSD)')
    parser.add_argument('--modes', type=str, default=None,
                       help='Режимы через запятую (swing,intraday,scalping)')
    parser.add_argument('--all', action='store_true',
                       help='Все символы + все режимы')
    
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
    """Бэктест с учётом режима."""
    tf_name = args.tf
    tf_value = TIMEFRAMES[tf_name]
    
    # Загрузка режима, если указан
    mode = None
    if args.mode:
        mode = get_mode(args.mode)
        print(f"\n[INFO] РЕЖИМ: {mode['name']}")
        print(f"[INFO] ТФ: {mode['timeframes']}")
        print(f"[INFO] MTF-фильтр: {mode.get('use_mtf_filter', False)}")
        # Используем ТФ из режима
        tf_name = mode['timeframes'][0]
        tf_value = TIMEFRAMES[tf_name]
    
    print("=" * 60)
    print(f" BACKTEST — {args.symbol} {tf_name} — {args.candles} candles")
    if mode:
        print(f" Режим: {mode['name']}")
    print("=" * 60)
    
    # Загрузка данных
    df = load_data_for_tf(args.symbol, tf_name, args.candles)
    print(f"[OK] Загружено {len(df)} свечей.")
    
    # Параметры из режима
    zigzag_len = mode['zigzag_length'] if mode else args.zigzag
    impulse_atr = mode['impulse_atr'] if mode else IMPULSE_ATR
    diagonal_atr = mode['diagonal_atr'] if mode else DIAGONAL_ATR
    correction_atr = mode['correction_atr'] if mode else CORRECTION_ATR
    max_bars = mode['max_bars_hold'] if mode else args.max_bars
    
    # Анализ
    pivots, impulses, diagonals, corrections = analyze_symbol(
        df, zigzag_len, USE_FILTER, impulse_atr, diagonal_atr, correction_atr
    )
    print(f"[OK] Импульсов: {len(impulses)}, Диагоналей: {len(diagonals)}, Коррекций: {len(corrections)}")
    
    # MTF-фильтр
    mtf_filter = None
    if mode and mode.get('use_mtf_filter'):
        mtf_tf = mode.get('mtf_timeframe', 'H4')
        print(f"\n[INFO] Загрузка MTF-контекста ({mtf_tf})...")
        mtf_data = load_data_for_tf(args.symbol, mtf_tf, args.candles)
        mtf_filter = MTFFilter(mtf_timeframe=mtf_tf)
        mtf_filter.update_trend(mtf_data)
        print(f"[OK] MTF тренд: {mtf_filter.trend}")
    
    # Выбор стратегий
    if args.all_strategies:
        strategies_to_run = list_strategies()
    elif args.strategy:
        strategies_to_run = [s.strip() for s in args.strategy.split(',')]
    elif mode and 'strategies' in mode:
        strategies_to_run = mode['strategies']  # из профиля
    else:
        strategies_to_run = ['w2_w3']
    
    print(f"\n[INFO] Запуск стратегий: {strategies_to_run}")
    
    all_results = {}
    
    for strat_name in strategies_to_run:
        try:
            StrategyClass = get_strategy(strat_name)
            
            # Передаём target_ratio для стратегий w2_w3 и w4_w5
            if strat_name == 'w2_w3' and mode and 'target_w2_w3' in mode:
                strategy = StrategyClass(target_ratio=mode['target_w2_w3'])
            elif strat_name == 'w4_w5' and mode and 'target_w4_w5' in mode:
                strategy = StrategyClass(target_ratio=mode['target_w4_w5'])
            else:
                strategy = StrategyClass()
            
            signals = strategy.generate_signals(df, impulses, diagonals, corrections, [])
            
            # MTF-фильтр
            if mtf_filter:
                before = len(signals)
                signals = mtf_filter.filter_signals(signals)
                print(f"\n[{strat_name}] MTF-фильтр: {before} -> {len(signals)} сигналов")
            
            if not signals:
                print(f"[{strat_name}] Нет сигналов.")
                all_results[strat_name] = {'total_trades': 0, 'winrate': 0, 'profit_factor': 0}
                continue
            
            # Trailing stop из режима
            use_trailing = mode.get('use_trailing_stop', False) if mode else False
            trailing_trigger = mode.get('trailing_trigger', 0.5) if mode else 0.5
            trailing_distance = mode.get('trailing_distance', 0.3) if mode else 0.3
            
            engine = BacktestEngine(
                max_bars_hold=max_bars,
                symbol=args.symbol,
                use_trailing_stop=use_trailing,
                trailing_trigger=trailing_trigger,
                trailing_distance=trailing_distance,
            )
            trades = engine.run(signals, df)
            
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
        print(f"{'Strategy':<15} {'Trades':<8} {'Winrate':<10} {'PF':<8} {'Return':<12}")
        print("-" * 70)
        for name, m in all_results.items():
            if m.get('total_trades', 0) > 0:
                print(f"{name:<15} {m['total_trades']:<8} "
                      f"{m['winrate']*100:>6.1f}%   "
                      f"{m['profit_factor']:>5.2f}   "
                      f"{m['total_return']:>+8.1f} pips")
        print("=" * 70)
        print()


def run_single_tf(args, tf_name):
    print("=" * 60)
    print(f" Elliott Wave Full Analysis")
    print(f" {args.symbol} | {tf_name} | {args.candles} candles")
    print("=" * 60)
    
    df = load_data_for_tf(args.symbol, tf_name, args.candles)
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


def run_live(args):
    """Запуск Live-режима."""
    from live.runner_multi import MultiLiveRunner
    
    # Определяем символы
    if args.all:
        symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD']
        modes = ['swing', 'intraday', 'scalping']
    elif args.symbols:
        symbols = [s.strip() for s in args.symbols.split(',')]
        modes = [m.strip() for m in args.modes.split(',')] if args.modes else [args.mode or 'swing']
    else:
        symbols = [args.symbol]
        modes = [args.mode or 'intraday']
    
    print(f" Symbols: {symbols}")
    print(f" Modes: {modes}")
    
    runner = MultiLiveRunner(
        symbols=symbols,
        modes=modes,
        strategies=args.strategy.split(',') if args.strategy else None,
        candles=args.candles,
        interval=args.interval,
    )
    
    runner.run()


def main():
    args = parse_args()
    
    if args.live:
        run_live(args)
    elif args.backtest:
        run_backtest(args)
    elif args.mtf:
        run_mtf(args)
    else:
        # Если указан режим — используем его ТФ
        if args.mode:
            mode = get_mode(args.mode)
            tf_name = mode['timeframes'][0]
            print(f"[INFO] Режим: {mode['name']} -> ТФ: {tf_name}")
            run_single_tf(args, tf_name)
        else:
            run_single_tf(args, args.tf)


if __name__ == "__main__":
    main()

