"""
Run All Backtests - Автоматический запуск всех комбинаций.

Запускает бэктесты через subprocess, сохраняет вывод в файлы.
"""
import sys
import os
import subprocess
from datetime import datetime


# ============================================================
# НАСТРОЙКИ
# ============================================================
COMBINATIONS = [
    # Swing
    ('swing', 'EURUSD', 'H4', 5000),
    ('swing', 'GBPUSD', 'H4', 5000),
    ('swing', 'USDJPY', 'H4', 5000),
    ('swing', 'XAUUSD', 'H4', 5000),
    # Intraday M30
    ('intraday', 'EURUSD', 'M30', 5000),
    ('intraday', 'GBPUSD', 'M30', 5000),
    ('intraday', 'XAUUSD', 'M30', 5000),
    ('intraday', 'USDJPY', 'M30', 5000),
    # Scalping
    ('scalping', 'EURUSD', 'M5', 5000),
    ('scalping', 'EURUSD', 'M15', 5000),
    ('scalping', 'GBPUSD', 'M5', 5000),
    ('scalping', 'GBPUSD', 'M15', 5000),
    ('scalping', 'XAUUSD', 'M5', 5000),
    ('scalping', 'XAUUSD', 'M15', 5000),
]


def main():
    print("=" * 80)
    print(" RUN ALL BACKTESTS")
    print("=" * 80)
    print(f" Всего комбинаций: {len(COMBINATIONS)}")
    print("=" * 80)
    
    output_dir = 'backtest_logs'
    os.makedirs(output_dir, exist_ok=True)
    
    for i, (mode, symbol, tf, candles) in enumerate(COMBINATIONS, 1):
        print(f"\n[{i}/{len(COMBINATIONS)}] {mode} | {symbol} | {tf}")
        
        cmd = [
            sys.executable, 'main_mpl.py',
            '--backtest',
            '--mode', mode,
            '--symbol', symbol,
            '--tf', tf,
            '--candles', str(candles),
        ]
        
        log_file = os.path.join(output_dir, f"{mode}_{symbol}_{tf}.txt")
        
        try:
            # Запуск с сохранением в файл
            with open(log_file, 'w', encoding='utf-8') as f:
                result = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=600,
                )
            
            if result.returncode == 0:
                print(f"  [OK] Сохранено: {log_file}")
            else:
                print(f"  [WARN] Завершено с кодом: {result.returncode}")
                print(f"         Лог: {log_file}")
        
        except subprocess.TimeoutExpired:
            print(f"  [TIMEOUT] {mode} | {symbol} | {tf}")
        except Exception as e:
            print(f"  [ERROR] {mode} | {symbol} | {tf}: {e}")
    
    print("\n" + "=" * 80)
    print(" ВСЕ БЭКТЕСТЫ ЗАВЕРШЕНЫ!")
    print("=" * 80)
    print(f" Логи: {output_dir}/")


if __name__ == "__main__":
    main()
