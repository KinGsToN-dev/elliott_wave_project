"""
Диагностика стратегий Wyckoff - почему 0 сигналов.
"""
import sys
sys.path.insert(0, '.')

from data.mt5_connector import MT5Connector
from mtf.multi_timeframe import TIMEFRAMES
from backtest.strategies.wyckoff_spring import WyckoffSpringStrategy
from backtest.strategies.wyckoff_utad import WyckoffUTADStrategy
from backtest.strategies.wyckoff_combined import WyckoffCombinedStrategy


def debug_strategy(name, cls, df):
    s = cls()
    analysis = s.detector.detect_all(df)
    
    print(f"\n{'=' * 60}")
    print(f" STRATEGY: {name}")
    print(f"{'=' * 60}")
    print(f" Ranges: {len(analysis.ranges)}")
    print(f" Events: {len(analysis.events)}")
    print(f" Phase: {analysis.current_phase}")
    
    types = {}
    for e in analysis.events:
        types[e.type] = types.get(e.type, 0) + 1
    print(f" Event types: {types}")
    
    for event_type in ('Spring', 'UT'):
        events = [e for e in analysis.events if e.type == event_type]
        if not events:
            print(f"\n {event_type}: NOT FOUND in events")
            continue
        
        print(f"\n {event_type}: {len(events)} found")
        ema200 = df['close'].ewm(span=200, adjust=False).mean()
        
        for ev in events:
            sig = s._check_event(analysis, ev, df)
            idx = min(ev.idx + 1, len(df) - 1)
            cur_ema = ema200.iloc[idx]
            cur_close = df.iloc[idx]['close']
            
            ema_ok = False
            if sig:
                if sig['direction'] == 'BUY':
                    ema_ok = cur_close > cur_ema
                else:
                    ema_ok = cur_close < cur_ema
            
            print(f"   {event_type} @ idx={ev.idx}")
            print(f"     _check_event: {'PASS' if sig else 'FAIL'}")
            if sig:
                print(f"     direction={sig['direction']}")
                print(f"     close={cur_close:.5f}, EMA200={cur_ema:.5f}")
                print(f"     EMA filter: {'PASS' if ema_ok else 'FAIL'}")


def main():
    c = MT5Connector(symbol='EURUSD', timeframe=TIMEFRAMES['H4'])
    c.connect()
    df = c.get_candles(count=500)
    c.disconnect()
    
    print(f"Data: {len(df)} bars, price {df['close'].min():.5f}-{df['close'].max():.5f}")
    
    debug_strategy("Spring", WyckoffSpringStrategy, df)
    debug_strategy("UTAD", WyckoffUTADStrategy, df)
    debug_strategy("Combined", WyckoffCombinedStrategy, df)


if __name__ == "__main__":
    main()