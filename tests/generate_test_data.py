"""
Генератор синтетических данных с известными волнами.
Добавлены все типы коррекций.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def generate_zigzag_candles(points, bars_per_leg=20, noise=0.00005, pad_bars=10):
    candles = []
    start_time = datetime(2026, 1, 1, 0, 0, 0)
    np.random.seed(42)
    
    first_price = points[0]
    for _ in range(pad_bars):
        o = first_price + np.random.randn() * noise
        c = first_price + np.random.randn() * noise
        h = max(o, c) + abs(np.random.randn() * noise)
        l = min(o, c) - abs(np.random.randn() * noise)
        candles.append({'time': start_time, 'open': o, 'high': h, 'low': l, 'close': c, 'tick_volume': 100})
        start_time += timedelta(hours=1)
    
    for i in range(len(points) - 1):
        p_start = points[i]
        p_end = points[i + 1]
        for j in range(bars_per_leg):
            t = j / bars_per_leg
            price = p_start + (p_end - p_start) * t
            o = price + np.random.randn() * noise
            c = price + (p_end - p_start) / bars_per_leg + np.random.randn() * noise
            h = max(o, c) + abs(np.random.randn() * noise)
            l = min(o, c) - abs(np.random.randn() * noise)
            candles.append({'time': start_time, 'open': o, 'high': h, 'low': l, 'close': c, 'tick_volume': np.random.randint(100, 1000)})
            start_time += timedelta(hours=1)
    
    last_price = points[-1]
    for _ in range(pad_bars):
        o = last_price + np.random.randn() * noise
        c = last_price + np.random.randn() * noise
        h = max(o, c) + abs(np.random.randn() * noise)
        l = min(o, c) - abs(np.random.randn() * noise)
        candles.append({'time': start_time, 'open': o, 'high': h, 'low': l, 'close': c, 'tick_volume': 100})
        start_time += timedelta(hours=1)
    
    df = pd.DataFrame(candles)
    df.set_index('time', inplace=True)
    return df


# ============================================================
# ИМПУЛЬСЫ И ДИАГОНАЛИ (из прошлых итераций)
# ============================================================
def make_bullish_impulse():
    return generate_zigzag_candles([1.1000, 1.1100, 1.1050, 1.1300, 1.1200, 1.1450], 20, pad_bars=10)

def make_bearish_impulse():
    return generate_zigzag_candles([1.2000, 1.1900, 1.1950, 1.1700, 1.1800, 1.1550], 20, pad_bars=10)

def make_invalid_w2_breaks_w1():
    return generate_zigzag_candles([1.1000, 1.1100, 1.0950, 1.1300, 1.1200, 1.1400], 20, pad_bars=10)

def make_invalid_w3_shortest():
    return generate_zigzag_candles([1.1000, 1.1100, 1.1050, 1.1080, 1.1050, 1.1200], 20, pad_bars=10)

def make_invalid_w4_overlaps_w1():
    return generate_zigzag_candles([1.1000, 1.1100, 1.1050, 1.1300, 1.1080, 1.1400], 20, pad_bars=10)

def make_truncated_5th():
    return generate_zigzag_candles([1.1000, 1.1100, 1.1050, 1.1300, 1.1200, 1.1280], 20, pad_bars=10)

def make_leading_contracting_bullish():
    return generate_zigzag_candles([1.1000, 1.1100, 1.1040, 1.1120, 1.1070, 1.1100], 20, pad_bars=10)

def make_ending_contracting_bullish():
    return generate_zigzag_candles([1.1000, 1.1120, 1.1060, 1.1150, 1.1095, 1.1130], 20, pad_bars=10)

def make_leading_expanding_bullish():
    return generate_zigzag_candles([1.1000, 1.1040, 1.1020, 1.1090, 1.1030, 1.1120], 20, pad_bars=10)

def make_bearish_contracting_diagonal():
    return generate_zigzag_candles([1.2000, 1.1900, 1.1960, 1.1880, 1.1930, 1.1900], 20, pad_bars=10)


# ============================================================
# КОРРЕКЦИИ (Итерация 4)
# ============================================================
def make_zigzag_correction():
    """
    Простой зигзаг 5-3-5.
    A -> B -> C, где W_B не заходит за начало W_A, W_C < W_A.
    """
    points = [
        1.1500,  # старт
        1.1400,  # A (вниз, -100 pips)
        1.1450,  # B (вверх, +50 pips, не заходит за старт A)
        1.1300,  # C (вниз, -150 pips, ниже A)
    ]
    return generate_zigzag_candles(points, bars_per_leg=30, pad_bars=10)


def make_double_zigzag():
    """
    Двойной зигзаг W-X-Y (3-3-3).
    """
    points = [
        1.1500,  # старт
        1.1450,  # W
        1.1480,  # X
        1.1400,  # Y
        1.1430,  # X2 (если нужно)
        1.1350,  # Z
    ]
    return generate_zigzag_candles(points, bars_per_leg=25, pad_bars=10)


def make_flat_regular():
    """
    Обычная плоскость 3-3-5.
    A ≈ B ≈ C, W_B откатывает ~90% W_A.
    """
    points = [
        1.1500,
        1.1450,  # A
        1.1500,  # B (≈ возврат к началу A)
        1.1400,  # C (≈ A)
    ]
    return generate_zigzag_candles(points, bars_per_leg=30, pad_bars=10)


def make_flat_expanded():
    """
    Расширенная плоскость 3-3-5.
    W_B > W_A, W_C > W_A.
    """
    points = [
        1.1500,
        1.1450,  # A
        1.1550,  # B (пробивает старт A)
        1.1350,  # C (пробивает A)
    ]
    return generate_zigzag_candles(points, bars_per_leg=30, pad_bars=10)


def make_flat_running():
    """
    Бегущая плоскость 3-3-5.
    W_B > W_A, но W_C < W_A (усечение).
    """
    points = [
        1.1500,
        1.1450,  # A
        1.1550,  # B (пробивает старт A)
        1.1460,  # C (не пробивает A — усечение)
    ]
    return generate_zigzag_candles(points, bars_per_leg=30, pad_bars=10)


def make_triangle_symmetric():
    """
    Симметричный треугольник A-B-C-D-E.
    A=0.01, B=0.008, C=0.006, D=0.005, E=0.004.
    """
    points = [1.1500, 1.1600, 1.1520, 1.1580, 1.1530, 1.1570]
    return generate_zigzag_candles(points, bars_per_leg=20, pad_bars=10)



def make_triangle_ascending():
    """
    Восходящий треугольник: D на уровне B, E пробивает вверх.
    """
    points = [1.1500, 1.1600, 1.1500, 1.1570, 1.1500, 1.1600]
    return generate_zigzag_candles(points, bars_per_leg=20, pad_bars=10)

def make_triangle_expanding():
    """
    Расширяющийся треугольник.
    A=0.002, B=0.004, C=0.008, D=0.012, E=0.021.
    """
    points = [1.1500, 1.1520, 1.1480, 1.1560, 1.1440, 1.1650]
    return generate_zigzag_candles(points, bars_per_leg=20, pad_bars=10)


def make_flat_data():
    np.random.seed(42)
    n = 300
    dates = [datetime(2026, 1, 1) + timedelta(hours=i) for i in range(n)]
    base = np.linspace(1.1000, 1.1010, n)
    noise = np.random.randn(n) * 0.00001
    prices = base + noise
    df = pd.DataFrame({
        'open': prices, 'high': prices + 0.00005, 'low': prices - 0.00005,
        'close': prices, 'tick_volume': [100] * n
    }, index=dates)
    return df

# ============================================================
# ФИБОНАЧЧИ (Итерация 5)
# ============================================================
def make_impulse_w3_161():
    """
    Импульс с W3 = 161.8% от W1.
    W1 = 0.0100, W3 = 0.01618 (161.8%).
    """
    points = [
        1.1000,   # 0
        1.1100,   # 1 (W1 = 0.0100)
        1.1050,   # 2
        1.12118,  # 3 (W3 = 1.1050 + 0.0100*1.618 = 1.12118)
        1.1150,   # 4
        1.1300,   # 5
    ]
    return generate_zigzag_candles(points, bars_per_leg=20, pad_bars=10)


def make_impulse_w5_100():
    """
    Импульс с W5 = 100% от W3.
    W3 = 0.0200, W5 = 0.0200.
    """
    points = [
        1.1000,   # 0
        1.1100,   # 1
        1.1050,   # 2
        1.1250,   # 3 (W3 = 0.0200)
        1.1150,   # 4
        1.1350,   # 5 (W5 = 0.0200)
    ]
    return generate_zigzag_candles(points, bars_per_leg=20, pad_bars=10)


def make_zigzag_wc_100():
    """
    Зигзаг с W_C = 100% от W_A.
    W_A = 0.0100, W_C = 0.0100.
    """
    points = [
        1.1500,   # 0
        1.1400,   # A (W_A = 0.0100)
        1.1450,   # B
        1.1300,   # C (W_C = 0.0100)
    ]
    return generate_zigzag_candles(points, bars_per_leg=30, pad_bars=10)


def make_zigzag_wc_161():
    """
    Зигзаг с W_C = 161.8% от W_A.
    W_A = 0.0100, W_C = 0.01618.
    """
    points = [
        1.1500,
        1.1400,   # A (W_A = 0.0100)
        1.1450,   # B
        1.12882,  # C (W_C = 1.1400 - 0.0100*1.618 = 1.12382... уточним)
    ]
    # Точнее: W_C = W_A * 1.618 = 0.01618
    # C = A - 0.01618 = 1.1400 - 0.01618 = 1.12382
    points = [1.1500, 1.1400, 1.1450, 1.12382]
    return generate_zigzag_candles(points, bars_per_leg=30, pad_bars=10)

# ============================================================
# КОМБИНАЦИИ (Итерация 6.5)
# ============================================================
def make_double_three():
    """
    Двойная тройка (W-X-Y).
    W: 0.0100 (вверх), X: 0.0040 (вниз, не заходит за начало W),
    Y: 0.0090 (вверх, пропорционально W).
    """
    points = [
        1.1000,  # 0: начало
        1.1100,  # W: 0.0100
        1.1060,  # X: 0.0040 (не заходит за 1.1000)
        1.1150,  # Y: 0.0090
    ]
    return generate_zigzag_candles(points, bars_per_leg=30, pad_bars=10)


def make_triple_three():
    """
    Тройная тройка (W-X-Y-X-Z).
    """
    points = [
        1.1000,  # 0
        1.1080,  # W
        1.1040,  # X
        1.1120,  # Y
        1.1080,  # X2
        1.1160,  # Z
    ]
    return generate_zigzag_candles(points, bars_per_leg=25, pad_bars=10)

if __name__ == "__main__":
    import os
    test_data_dir = os.path.join(os.path.dirname(__file__), "test_data")
    os.makedirs(test_data_dir, exist_ok=True)
    
    scenarios = {
        # Импульсы
        'bullish_impulse.csv': make_bullish_impulse(),
        'bearish_impulse.csv': make_bearish_impulse(),
        'invalid_w2.csv': make_invalid_w2_breaks_w1(),
        'invalid_w3.csv': make_invalid_w3_shortest(),
        'invalid_w4.csv': make_invalid_w4_overlaps_w1(),
        'truncated_5th.csv': make_truncated_5th(),
        # Диагонали
        'leading_contracting.csv': make_leading_contracting_bullish(),
        'ending_contracting.csv': make_ending_contracting_bullish(),
        'leading_expanding.csv': make_leading_expanding_bullish(),
        'bearish_contracting.csv': make_bearish_contracting_diagonal(),
        # Коррекции
        'corr_zigzag.csv': make_zigzag_correction(),
        'corr_double_zigzag.csv': make_double_zigzag(),
        'corr_flat_regular.csv': make_flat_regular(),
        'corr_flat_expanded.csv': make_flat_expanded(),
        'corr_flat_running.csv': make_flat_running(),
        'corr_triangle_symmetric.csv': make_triangle_symmetric(),
        'corr_triangle_ascending.csv': make_triangle_ascending(),
        'corr_triangle_expanding.csv': make_triangle_expanding(),
        # Плоские
        'flat_data.csv': make_flat_data(),
        # Фибоначчи
        'fib_w3_161.csv': make_impulse_w3_161(),
        'fib_w5_100.csv': make_impulse_w5_100(),
        'fib_wc_100.csv': make_zigzag_wc_100(),
        'fib_wc_161.csv': make_zigzag_wc_161(),
        # Комбинации
        'comb_double_three.csv': make_double_three(),
        'comb_triple_three.csv': make_triple_three(),
    }
    
    for name, df in scenarios.items():
        path = os.path.join(test_data_dir, name)
        df.to_csv(path)
        print(f"[OK] Создан: {name} ({len(df)} свечей)")
    
    print("\n[DONE] Все тестовые данные сгенерированы.")

