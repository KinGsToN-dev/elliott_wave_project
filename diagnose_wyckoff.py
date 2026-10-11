"""
Диагностика WyckoffDetector на EURUSD H4.
"""
import sys
sys.path.insert(0, '.')

from data.mt5_connector import MT5Connector, MT5_AVAILABLE, generate_test_data
from mtf.multi_timeframe import TIMEFRAMES
from wyckoff.detector import WyckoffDetector
from wyckoff.ranges import TradingRangeDetector


def main():
    tf_value = TIMEFRAMES.get('H4', 16388)
    
    df = None
    if MT5_AVAILABLE:
        c = MT5Connector(symbol='EURUSD', timeframe=tf_value)
        if c.connect():
            df = c.get_candles(count=500)
            c.disconnect()
    
    if df is None:
        print("[WARN] MT5 недоступен, использую синтетику")
        df = generate_test_data(count=500)
    
    print(f"Загружено: {len(df)} свечей")
    print(f"Цена: {df['close'].min():.5f} - {df['close'].max():.5f}")
    print()
    
    # === 1. Проверка TradingRangeDetector ===
    print("=" * 60)
    print(" TRADING RANGE DETECTION")
    print("=" * 60)
    
    rd = TradingRangeDetector(
        min_bars=15,
        max_width_atr=5.0,
        touch_tolerance_atr=0.5,
    )
    ranges = rd.find_ranges(df)
    print(f"Найдено ranges: {len(ranges)}")
    
    for i, r in enumerate(ranges[:5]):
        print(f"  Range #{i}: [{r.lower:.5f}, {r.upper:.5f}] "
              f"bars={r.bars_count} width_atr={r.width_atr:.2f} "
              f"touches={r.touches_upper}/{r.touches_lower}")
    
    current = rd.get_current_range(df)
    print(f"Current range: {current}")
    print()
    
    print("=" * 60)
    print(" FULL WYCKOFF ANALYSIS")
    print("=" * 60)
    
    detector = WyckoffDetector(
    range_min_bars=15,
    range_max_width_atr=5.0,
    spring_depth_atr=1.5,
    climax_volume_mult=1.3,
    phase_trend_atr_threshold=0.5,
    phase_lookback_bars=30,
)
    result = detector.detect_all(df)
    
    print(f"Ranges: {len(result.ranges)}")
    print(f"Current range: {result.current_range is not None}")
    if result.current_range:
        r = result.current_range
        print(f"  [{r.lower:.5f}, {r.upper:.5f}] bars={r.bars_count}")
    
    print(f"Phase: {result.current_phase}")
    if result.current_phase:
        print(f"  phase={result.current_phase.phase.value}")
        print(f"  confidence={result.current_phase.confidence:.2f}")
        print(f"  reason={result.current_phase.reason}")
    
    print(f"Events: {len(result.events)}")
    for e in result.events:
        print(f"  {e.type} @ idx={e.idx} price={e.price:.5f} "
              f"vol={e.volume} dir={e.direction}")
    
    print(f"Volume signals: {len(result.volume_signals)}")
    for s in result.volume_signals[:5]:
        print(f"  {s.type} @ idx={s.idx} dir={s.direction}")
    
    print(f"Trendlines: {len(result.trendlines)}")
    print(f"Trendline breaks: {len(result.trendline_breaks)}")
    
    print()
    print(f"Summary: {result.summary}")


if __name__ == "__main__":
    main()