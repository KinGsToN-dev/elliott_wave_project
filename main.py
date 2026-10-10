"""
Main - Точка входа. Итерация 3: Импульсы + Диагонали.
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.mt5_connector import MT5Connector, generate_test_data, MT5_AVAILABLE
from core.zigzag import ZigZag
from patterns.impulse import ImpulseDetector
from patterns.diagonal import DiagonalDetector
from visualization.chart import EWChart

# ============================================================
# НАСТРОЙКИ
# ============================================================
SYMBOL = "EURUSD"
TIMEFRAME = 16385          # H1
CANDLES_COUNT = 500
ZIGZAG_LENGTH = 5
MIN_ATR_RATIO = 1.5
MAX_SHOW = 5


def main():
    print("=" * 60)
    print(" Elliott Wave Project - Iteration 3: Impulses + Diagonals")
    print("=" * 60)
    
    df = None
    if MT5_AVAILABLE:
        connector = MT5Connector(symbol=SYMBOL, timeframe=TIMEFRAME)
        if connector.connect():
            df = connector.get_candles(count=CANDLES_COUNT)
            connector.disconnect()
    
    if df is None:
        df = generate_test_data(count=CANDLES_COUNT)
    
    print(f"\n[INFO] Загружено {len(df)} свечей.")
    
    # --- ZigZag ---
    zigzag = ZigZag(df, length=ZIGZAG_LENGTH)
    pivots = zigzag.find_pivots()
    
    # --- Импульсы ---
    print(f"\n[INFO] Поиск импульсов...")
    imp_detector = ImpulseDetector(pivots, df=df, min_atr_ratio=MIN_ATR_RATIO)
    impulses = imp_detector.find_impulses()
    
    # --- Диагонали ---
    print(f"\n[INFO] Поиск диагоналей...")
    diag_detector = DiagonalDetector(pivots, df=df, min_atr_ratio=MIN_ATR_RATIO)
    diagonals = diag_detector.find_diagonals()
    
    # --- Информация ---
    if impulses:
        print(f"\n[INFO] Импульсов: {len(impulses)}")
        for imp in impulses[-3:]:
            print(f"  {imp['direction']:8} | Size: {imp['size']*10000:.0f} pips | Ext: {imp['extension'] or '—'}")
    
    if diagonals:
        print(f"\n[INFO] Диагоналей: {len(diagonals)}")
        for d in diagonals[-3:]:
            print(f"  {d['direction']:8} | {d['shape']:12} | Size: {d['size']*10000:.0f} pips")
    
    # --- Визуализация ---
    print(f"\n[INFO] Построение графика...")
    chart = EWChart(title=f"{SYMBOL} - EW Analysis")
    chart.load_data(df)
    chart.add_zigzag(pivots, color='#FFD700', width=1)
    
    if impulses:
        chart.add_impulses(impulses, max_show=MAX_SHOW)
        chart.add_wave_labels(impulses, max_show=MAX_SHOW)
    
    if diagonals:
        chart.add_diagonals(diagonals, max_show=MAX_SHOW)
        chart.add_diagonal_labels(diagonals, max_show=MAX_SHOW)
    
    chart.show()
    print("\n[OK] Готово!")


if __name__ == "__main__":
    main()
