"""
Визуализация Wyckoff-разметки.

Показывает свечи, Trading Range, Events, Trendlines, Volume.
"""
import sys
import os
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle
from datetime import datetime

from data.mt5_connector import MT5Connector, MT5_AVAILABLE, generate_test_data
from mtf.multi_timeframe import TIMEFRAMES
from wyckoff.detector import WyckoffDetector


def load_data(symbol, tf_name, count):
    """Загрузка данных."""
    tf_value = TIMEFRAMES.get(tf_name, 16388)
    
    if MT5_AVAILABLE:
        c = MT5Connector(symbol=symbol, timeframe=tf_value)
        if c.connect():
            df = c.get_candles(count=count)
            c.disconnect()
            if df is not None and len(df) > 20:
                return df
    
    print("[WARN] MT5 недоступен, использую синтетику")
    return generate_test_data(count=count)


def visualize(symbol='EURUSD', tf_name='H4', count=500, save=True):
    """
    Визуализация Wyckoff-разметки.
    """
    print(f"=== Загрузка {symbol} {tf_name} ===")
    df = load_data(symbol, tf_name, count)
    
    if df is None or len(df) < 50:
        print("[ERROR] Недостаточно данных")
        return
    
    print(f"Загружено: {len(df)} свечей")
    print(f"Цена: {df['close'].min():.5f} - {df['close'].max():.5f}")
    
    # Анализ с ослабленными параметрами (для отладки)
    detector = WyckoffDetector(
        range_min_bars=15,
        range_max_width_atr=5.0,
        spring_depth_atr=1.5,
        climax_volume_mult=1.3,
        phase_trend_atr_threshold=0.5,
        phase_lookback_bars=30,
    )

    print("=== Анализ Wyckoff ===")
    result = detector.detect_all(df)

    print(f"Ranges: {len(result.ranges)}")
    for i, r in enumerate(result.ranges):
        print(f"  R{i}: [{r.lower:.5f}, {r.upper:.5f}] bars={r.bars_count}")

    # Детальный анализ каждого range
    from wyckoff.events import WyckoffEventDetector
    ed = WyckoffEventDetector()
    print()
    print("=== Поиск events в каждом range ===")
    for i, r in enumerate(result.ranges):
        events = ed.detect_all(df, r)
        print(f"  R{i}: {len(events)} events")
        for e in events:
            print(f"    {e.type} @ idx={e.idx}")

    
    
    print(f"Current range: {result.current_range is not None}")
    print(f"Events: {len(result.events)}")
    for e in result.events:
        print(f"  {e.type} @ idx={e.idx} price={e.price:.5f} dir={e.direction}")
    print(f"Phase: {result.current_phase}")
    print(f"Trendlines: {len(result.trendlines)}")
    
    # === Рисуем ===
    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(18, 10),
        gridspec_kw={'height_ratios': [3, 1]},
    )
    
    # Заголовок
    phase_str = 'None'
    if result.current_phase:
        phase_str = (f"{result.current_phase.phase.value.upper()} "
                     f"(conf={result.current_phase.confidence:.2f})")
    
    ax1.set_title(
        f"{symbol} {tf_name} — Wyckoff | "
        f"Phase: {phase_str} | "
        f"Ranges: {len(result.ranges)} | "
        f"Events: {len(result.events)}",
        fontsize=14, fontweight='bold',
    )
    
    # === 1. Свечи ===
    x = np.arange(len(df))
    width = 0.6
    
    for i, (time, row) in enumerate(df.iterrows()):
        color = '#26a69a' if row['close'] >= row['open'] else '#ef5350'
        # Тень
        ax1.plot([i, i], [row['low'], row['high']], color=color, linewidth=0.5)
        # Тело
        body_bottom = min(row['open'], row['close'])
        body_height = abs(row['close'] - row['open'])
        ax1.add_patch(Rectangle(
            (i - width/2, body_bottom), width, body_height,
            facecolor=color, edgecolor=color,
        ))
    
    # === 2. Trading Ranges ===
    for i, r in enumerate(result.ranges):
        # Прямоугольник
        rect = Rectangle(
            (r.start_idx, r.lower),
            r.end_idx - r.start_idx,
            r.upper - r.lower,
            facecolor='yellow', edgecolor='orange',
            alpha=0.15, linewidth=2, linestyle='--',
        )
        ax1.add_patch(rect)
        
        # Подпись
        ax1.text(
            r.start_idx, r.upper,
            f"R{i} [{r.width_atr:.1f} ATR, {r.bars_count}b]",
            fontsize=8, color='orange', fontweight='bold',
            verticalalignment='bottom',
        )
    
    # Текущий range — жирнее
    if result.current_range:
        r = result.current_range
        rect = Rectangle(
            (r.start_idx, r.lower),
            r.end_idx - r.start_idx,
            r.upper - r.lower,
            facecolor='none', edgecolor='red',
            alpha=1.0, linewidth=3, linestyle='-',
        )
        ax1.add_patch(rect)
        ax1.text(
            r.start_idx, r.lower,
            " CURRENT ",
            fontsize=10, color='white', fontweight='bold',
            backgroundcolor='red',
        )
    
    # === 3. Trendlines ===
    line_colors = {
        'support': 'blue',
        'supply': 'red',
        'overbought': 'purple',
        'oversold': 'green',
    }
    line_styles = {
        'support': '-',
        'supply': '-',
        'overbought': '--',
        'oversold': '--',
    }
    
    for line in result.trendlines:
        color = line_colors.get(line.type.value, 'gray')
        style = line_styles.get(line.type.value, '-')
        
        # Продлеваем линию до конца df
        x_vals = [line.x1, min(line.x2 + 30, len(df) - 1)]
        y_vals = [line.get_value(x_vals[0]), line.get_value(x_vals[1])]
        
        ax1.plot(
            x_vals, y_vals,
            color=color, linestyle=style, linewidth=1.5,
            label=f"{line.type.value} (touches={line.touches})",
        )
    
    # === 4. Events ===
    event_colors = {
        'SC': 'lime',
        'AR': 'green',
        'ST': 'darkgreen',
        'Spring': 'cyan',
        'Test': 'teal',
        'SOS': 'gold',
        'LPS': 'orange',
        'UT': 'red',
        'UTAD': 'darkred',
        'SOW': 'purple',
        'LPSY': 'magenta',
    }
    
    event_markers = {
        'SC': '^',
        'AR': 'v',
        'ST': 'o',
        'Spring': 'D',
        'Test': 's',
        'SOS': '^',
        'LPS': 'o',
        'UT': 'v',
        'UTAD': 'D',
        'SOW': 'v',
        'LPSY': 's',
    }
    
    for e in result.events:
        color = event_colors.get(e.type, 'gray')
        marker = event_markers.get(e.type, 'o')
        
        if e.direction == 'bullish':
            # Снизу
            ax1.scatter(
                e.idx, e.price * 0.998,
                marker=marker, color=color, s=120,
                edgecolors='black', linewidths=1, zorder=5,
            )
            ax1.annotate(
                e.type, (e.idx, e.price * 0.998),
                textcoords="offset points", xytext=(0, -15),
                ha='center', fontsize=8, fontweight='bold', color=color,
            )
        else:
            # Сверху
            ax1.scatter(
                e.idx, e.price * 1.002,
                marker=marker, color=color, s=120,
                edgecolors='black', linewidths=1, zorder=5,
            )
            ax1.annotate(
                e.type, (e.idx, e.price * 1.002),
                textcoords="offset points", xytext=(0, 10),
                ha='center', fontsize=8, fontweight='bold', color=color,
            )
    
    # === 5. Оформление ax1 ===
    ax1.set_ylabel('Price', fontsize=12)
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper left', fontsize=8)
    
    # === 6. Volume (ax2) ===
    volumes = df['tick_volume'].values
    colors = ['#26a69a' if df['close'].iloc[i] >= df['open'].iloc[i]
              else '#ef5350' for i in range(len(df))]
    ax2.bar(x, volumes, color=colors, width=0.8, alpha=0.7)
    ax2.set_ylabel('Volume', fontsize=12)
    ax2.set_xlabel('Bar Index', fontsize=12)
    ax2.grid(True, alpha=0.3)
    
    # Volume MA
    vol_ma = df['tick_volume'].rolling(20).mean()
    ax2.plot(x, vol_ma, color='orange', linewidth=1, label='MA20')
    ax2.legend(loc='upper left', fontsize=8)
    
    plt.tight_layout()
    
    if save:
        filename = f"wyckoff_{symbol}_{tf_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.png"
        plt.savefig(filename, dpi=100, bbox_inches='tight')
        print(f"\n[OK] Сохранено: {filename}")
    
    plt.show()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', default='EURUSD')
    parser.add_argument('--tf', default='H4')
    parser.add_argument('--candles', type=int, default=500)
    args = parser.parse_args()
    
    visualize(args.symbol, args.tf, args.candles)