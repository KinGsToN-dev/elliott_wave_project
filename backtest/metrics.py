"""
Metrics - Расчёт метрик бэктеста.
"""
import pandas as pd
import numpy as np


class BacktestMetrics:
    """Расчёт метрик по сделкам."""
    
    def __init__(self, trades):
        self.trades = trades
    
    def calculate(self):
        """Возвращает все метрики."""
        if not self.trades:
            return {
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'winrate': 0,
                'total_return': 0,
                'profit_factor': 0,
                'max_drawdown': 0,
                'avg_win': 0,
                'avg_loss': 0,
            }
        
        pnls = [t['pnl'] for t in self.trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        
        total_return = sum(pnls)
        winrate = len(wins) / len(pnls) if pnls else 0
        
        profit_factor = 0
        if losses:
            profit_factor = sum(wins) / abs(sum(losses))
        elif wins:
            profit_factor = float('inf')
        
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        
        max_dd = self._calculate_max_drawdown(pnls)
        
        # Причины выхода
        tp_count = sum(1 for t in self.trades if t['exit_reason'] == 'TP')
        sl_count = sum(1 for t in self.trades if t['exit_reason'] == 'SL')
        time_count = sum(1 for t in self.trades if t['exit_reason'] == 'TIME')
        
        return {
            'total_trades': len(self.trades),
            'wins': len(wins),
            'losses': len(losses),
            'winrate': winrate,
            'total_return': total_return,
            'profit_factor': profit_factor,
            'max_drawdown': max_dd,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'tp_count': tp_count,
            'sl_count': sl_count,
            'time_count': time_count,
        }
    
    def _calculate_max_drawdown(self, pnls):
        """Максимальная просадка от пика."""
        if not pnls:
            return 0
        
        cumsum = np.cumsum(pnls)
        running_max = np.maximum.accumulate(cumsum)
        drawdown = cumsum - running_max
        return float(min(drawdown))
    
    def print_summary(self, strategy_name="Unknown"):
        """Выводит метрики в консоль."""
        m = self.calculate()
        
        print()
        print("=" * 60)
        print(f" BACKTEST RESULTS — {strategy_name}")
        print("=" * 60)
        print(f" Всего сделок:  {m['total_trades']}")
        print(f" Прибыльных:    {m['wins']} ({m['winrate']*100:.1f}%)")
        print(f" Убыточных:     {m['losses']}")
        print("-" * 60)
        print(f" Total Return:  {m['total_return']:+.1f} pips")
        print(f" Profit Factor: {m['profit_factor']:.2f}")
        print(f" Max Drawdown:  {m['max_drawdown']:.1f} pips")
        print(f" Avg Win:       {m['avg_win']:+.1f} pips")
        print(f" Avg Loss:      {m['avg_loss']:+.1f} pips")
        print("-" * 60)
        print(f" Выходы: TP={m['tp_count']} | SL={m['sl_count']} | TIME={m['time_count']}")
        print("=" * 60)
        print()
        
        return m
