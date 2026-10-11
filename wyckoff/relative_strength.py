"""
Wyckoff Relative Strength - сравнение актива с эталоном.

Основано на книге Хатсона (стр. 20, 23-24):
- На бычьем рынке ищем СИЛЬНЫЕ группы, которые сопротивляются падению.
- На медвежьем рынке ищем СЛАБЫЕ группы, которые не растут с рынком.

Relative Strength (RS):
- RS = asset_close / benchmark_close
- RS растёт → актив сильнее эталона
- RS падает → актив слабее эталона

Применение:
- Сильный RS в Accumulation → кандидат на покупку
- Слабый RS в Distribution → кандидат на продажу
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple

from wyckoff.ranges import TradingRange


@dataclass
class RSResult:
    """Результат анализа Relative Strength."""
    rs_value: float              # текущее значение RS (asset/benchmark)
    rs_trend: str                # 'rising', 'falling', 'flat'
    rs_rank: float               # процентиль 0..100 (100 = максимум за период)
    is_stronger: bool            # растёт ли RS
    rs_change_pct: float         # % изменения RS за период
    period_bars: int             # за сколько баров считали
    meta: Dict = field(default_factory=dict)
    
    def __repr__(self):
        return (
            f"RSResult(value={self.rs_value:.4f}, "
            f"trend={self.rs_trend}, rank={self.rs_rank:.1f}%, "
            f"stronger={self.is_stronger})"
        )


@dataclass
class RSAtRange:
    """Анализ RS внутри Trading Range."""
    range_obj: TradingRange
    rs_before: float             # RS до range
    rs_after: float              # RS после range
    rs_in_range: float           # RS внутри range
    trend: str                   # 'rising', 'falling', 'flat'
    behavior_at_highs: str       # 'stronger', 'weaker', 'same'
    behavior_at_lows: str        # 'stronger', 'weaker', 'same'
    interpretation: str          # текстовая интерпретация
    
    def __repr__(self):
        return (
            f"RSAtRange(trend={self.trend}, "
            f"highs={self.behavior_at_highs}, "
            f"lows={self.behavior_at_lows})"
        )


class RelativeStrengthAnalyzer:
    """
    Анализ Relative Strength (RS).
    """
    
    def __init__(
        self,
        trend_period: int = 20,
        rank_period: int = 100,
        flat_threshold: float = 0.002,  # 0.2% для определения flat
    ):
        """
        Параметры:
        ----------
        trend_period : int
            Период для определения тренда RS.
        rank_period : int
            Период для вычисления процентиля.
        flat_threshold : float
            Порог для "флэт" (в долях от значения RS).
        """
        self.trend_period = trend_period
        self.rank_period = rank_period
        self.flat_threshold = flat_threshold
    
    def _validate_data(
        self,
        asset_df: pd.DataFrame,
        benchmark_df: pd.DataFrame,
    ) -> bool:
        """Проверяет, что данные корректны."""
        if asset_df is None or benchmark_df is None:
            return False
        if 'close' not in asset_df.columns or 'close' not in benchmark_df.columns:
            return False
        if len(asset_df) < 2 or len(benchmark_df) < 2:
            return False
        return True
    
    def _align_data(
        self,
        asset_df: pd.DataFrame,
        benchmark_df: pd.DataFrame,
    ) -> Tuple[pd.Series, pd.Series]:
        """
        Выравнивает данные по общим timestamp.
        """
        # Приводим индексы к общему типу
        asset_close = asset_df['close']
        benchmark_close = benchmark_df['close']
        
        # Если индексы одинаковые (обычно так и есть) — просто возвращаем
        if asset_close.index.equals(benchmark_close.index):
            return asset_close, benchmark_close
        
        # Иначе — inner join
        combined = pd.concat([
            asset_close.rename('asset'),
            benchmark_close.rename('benchmark'),
        ], axis=1).dropna()
        
        return combined['asset'], combined['benchmark']
    
    def compute_rs(
        self,
        asset_df: pd.DataFrame,
        benchmark_df: pd.DataFrame,
    ) -> Optional[pd.Series]:
        """
        RS = asset_close / benchmark_close.
        
        Возвращает Series с индексом timestamp.
        """
        if not self._validate_data(asset_df, benchmark_df):
            return None
        
        asset_close, benchmark_close = self._align_data(asset_df, benchmark_df)
        
        if len(asset_close) == 0:
            return None
        
        # Избегаем деления на 0
        benchmark_close = benchmark_close.replace(0, np.nan)
        rs = asset_close / benchmark_close
        rs = rs.dropna()
        
        return rs
    
    def find_rs_trend(
        self,
        rs_series: pd.Series,
    ) -> str:
        """
        Определяет тренд RS через линейную регрессию.
        
        Использует slope регрессии, нормализованный на среднее значение:
        - slope_pct > flat_threshold → 'rising'
        - slope_pct < -flat_threshold → 'falling'
        - иначе → 'flat'
        """
        if rs_series is None or len(rs_series) < 2:
            return 'flat'
        
        period = min(self.trend_period, len(rs_series))
        recent = rs_series.iloc[-period:].dropna()
        
        if len(recent) < 2:
            return 'flat'
        
        first = float(recent.iloc[0])
        last = float(recent.iloc[-1])
        mean = float(recent.mean())
        
        if mean == 0:
            return 'flat'
        
        change_pct = (last - first) / abs(mean)
        
        if change_pct > self.flat_threshold:
            return 'rising'
        elif change_pct < -self.flat_threshold:
            return 'falling'
        return 'flat'
        
        # Линейная регрессия
        x = np.arange(len(recent), dtype=float)
        y = recent.values.astype(float)
        
        # Защита от NaN
        mask = ~np.isnan(y)
        if mask.sum() < 2:
            return 'flat'
        
        x = x[mask]
        y = y[mask]
        
        # slope = cov(x,y) / var(x)
        x_mean = x.mean()
        y_mean = y.mean()
        
        denominator = ((x - x_mean) ** 2).sum()
        if denominator == 0:
            return 'flat'
        
        slope = ((x - x_mean) * (y - y_mean)).sum() / denominator
        
        # Нормализуем slope на среднее значение
        if abs(y_mean) < 1e-9:
            return 'flat'
        
        slope_pct = (slope * len(recent)) / abs(y_mean)
        
        if slope_pct > self.flat_threshold:
            return 'rising'
        elif slope_pct < -self.flat_threshold:
            return 'falling'
        return 'flat'
    
    def find_rs_rank(
        self,
        rs_series: pd.Series,
    ) -> float:
        """
        Процентиль текущего RS относительно последних rank_period баров.
        100 = максимум, 0 = минимум.
        """
        if rs_series is None or len(rs_series) < 2:
            return 50.0
        
        period = min(self.rank_period, len(rs_series))
        recent = rs_series.iloc[-period:]
        
        current = recent.iloc[-1]
        
        # Процент значений ниже текущего
        rank = (recent < current).sum() / len(recent) * 100
        return float(rank)
    
    def analyze(
        self,
        asset_df: pd.DataFrame,
        benchmark_df: pd.DataFrame,
    ) -> Optional[RSResult]:
        """
        Полный анализ RS.
        """
        rs_series = self.compute_rs(asset_df, benchmark_df)
        
        if rs_series is None or len(rs_series) == 0:
            return None
        
        trend = self.find_rs_trend(rs_series)
        rank = self.find_rs_rank(rs_series)
        
        current = float(rs_series.iloc[-1])
        
        # % изменения за trend_period
        period = min(self.trend_period, len(rs_series))
        if period > 1 and rs_series.iloc[-period] != 0:
            change_pct = (current - rs_series.iloc[-period]) / abs(rs_series.iloc[-period]) * 100
        else:
            change_pct = 0.0
        
        return RSResult(
            rs_value=current,
            rs_trend=trend,
            rs_rank=rank,
            is_stronger=(trend == 'rising' or rank >= 70.0),
            rs_change_pct=round(change_pct, 2),
            period_bars=period,
            meta={
                'min': float(rs_series.min()),
                'max': float(rs_series.max()),
                'mean': float(rs_series.mean()),
            },
        )
    
    def compare_at_range(
        self,
        asset_df: pd.DataFrame,
        benchmark_df: pd.DataFrame,
        r: TradingRange,
    ) -> Optional[RSAtRange]:
        """
        Сравнивает поведение актива и эталона внутри Trading Range.
        
        Проверяет:
        - Как ведёт себя актив на максимумах range (сильнее/слабее).
        - Как ведёт себя актив на минимумах range.
        """
        rs_series = self.compute_rs(asset_df, benchmark_df)
        
        if rs_series is None or len(rs_series) == 0:
            return None
        
        # RS до range (если есть)
        rs_before = None
        if r.start_idx > 0 and r.start_idx < len(rs_series):
            rs_before = float(rs_series.iloc[r.start_idx - 1])
        
        # RS после range (если есть)
        rs_after = None
        if r.end_idx + 1 < len(rs_series):
            rs_after = float(rs_series.iloc[r.end_idx + 1])
        
        # RS внутри range (среднее)
        start = max(0, r.start_idx)
        end = min(len(rs_series) - 1, r.end_idx)
        
        if start > end:
            return None
        
        rs_in = rs_series.iloc[start:end + 1]
        
        if len(rs_in) < 2:
            return None
        
        rs_in_range = float(rs_in.mean())
        
        # Тренд RS внутри range
        trend = self.find_rs_trend(rs_in)
        
        # Поведение на границах
        # На максимумах: RS должен расти, если актив сильнее
        # На минимумах: RS должен падать медленнее, если актив сильнее
        behavior_at_highs = self._analyze_at_boundaries(
            asset_df, benchmark_df, rs_series, r, boundary='high'
        )
        behavior_at_lows = self._analyze_at_boundaries(
            asset_df, benchmark_df, rs_series, r, boundary='low'
        )
        
        # Интерпретация
        if trend == 'rising' and behavior_at_highs == 'stronger':
            interp = 'СИЛЬНЫЙ: RS растёт, актив сильнее на максимумах'
        elif trend == 'falling' and behavior_at_lows == 'weaker':
            interp = 'СЛАБЫЙ: RS падает, актив слабее на минимумах'
        elif trend == 'rising':
            interp = 'УМЕРЕННО СИЛЬНЫЙ: RS растёт'
        elif trend == 'falling':
            interp = 'УМЕРЕННО СЛАБЫЙ: RS падает'
        else:
            interp = 'НЕЙТРАЛЬНЫЙ: RS стабилен'
        
        return RSAtRange(
            range_obj=r,
            rs_before=rs_before or rs_in_range,
            rs_after=rs_after or rs_in_range,
            rs_in_range=rs_in_range,
            trend=trend,
            behavior_at_highs=behavior_at_highs,
            behavior_at_lows=behavior_at_lows,
            interpretation=interp,
        )
    
    def _analyze_at_boundaries(
        self,
        asset_df: pd.DataFrame,
        benchmark_df: pd.DataFrame,
        rs_series: pd.Series,
        r: TradingRange,
        boundary: str,  # 'high' или 'low'
    ) -> str:
        """
        Анализирует поведение актива на границах range.
        
        Возвращает 'stronger', 'weaker', 'same'.
        """
        start = max(0, r.start_idx)
        end = min(len(rs_series) - 1, r.end_idx)
        
        if start >= end:
            return 'same'
        
        asset_sub = asset_df.iloc[start:end + 1]
        benchmark_sub = benchmark_df.iloc[start:end + 1]
        
        # Находим бары, где asset достигает границ
        if boundary == 'high':
            # Актив на максимуме range
            threshold = r.upper - (r.upper - r.lower) * 0.15
            mask = asset_sub['high'] >= threshold
        else:
            threshold = r.lower + (r.upper - r.lower) * 0.15
            mask = asset_sub['low'] <= threshold
        
        if not mask.any():
            return 'same'
        
        # Средний RS в этих барах
        rs_at_boundary = rs_series.iloc[start:end + 1][mask.values].mean()
        rs_overall = rs_series.iloc[start:end + 1].mean()
        
        if pd.isna(rs_at_boundary) or pd.isna(rs_overall):
            return 'same'
        
        # Сравниваем
        if boundary == 'high':
            # На максимуме: если RS выше среднего → сильнее
            if rs_at_boundary > rs_overall * 1.05:
                return 'stronger'
            elif rs_at_boundary < rs_overall * 0.95:
                return 'weaker'
        else:
            # На минимуме: если RS выше среднего → сильнее (не падает)
            if rs_at_boundary > rs_overall * 1.05:
                return 'stronger'
            elif rs_at_boundary < rs_overall * 0.95:
                return 'weaker'
        
        return 'same'
    
    def find_strongest(
        self,
        assets: Dict[str, pd.DataFrame],
        benchmark_df: pd.DataFrame,
    ) -> List[Tuple[str, RSResult]]:
        """
        Находит самые сильные активы среди переданных.
        
        Параметры:
        ----------
        assets : dict
            Словарь {symbol: df}.
        benchmark_df : pd.DataFrame
            Эталон.
        
        Возвращает:
        -----------
        List[Tuple[str, RSResult]]
            Отсортированный список (самый сильный первый).
        """
        results = []
        
        for symbol, asset_df in assets.items():
            result = self.analyze(asset_df, benchmark_df)
            if result is not None:
                results.append((symbol, result))
        
        # Сортируем по rank (высокий = сильный)
        results.sort(key=lambda x: x[1].rs_rank, reverse=True)
        
        return results