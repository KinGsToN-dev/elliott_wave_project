"""
Тесты для core.overlap_filter.OverlapFilter
"""
import pytest
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.overlap_filter import OverlapFilter


def make_pattern(start_time, end_time, direction='bullish'):
    """Хелпер для создания паттерна."""
    return {
        'start_time': start_time,
        'end_time': end_time,
        'direction': direction,
        'points': [
            (start_time, 1.1000, '0'),
            (end_time, 1.1100, '5'),
        ],
    }


class TestOverlapFilter:
    def test_no_patterns(self):
        """Пустые списки."""
        f = OverlapFilter([], [], [])
        imps, diags, corrs = f.filter()
        assert len(imps) == 0
        assert len(diags) == 0
        assert len(corrs) == 0
    
    def test_only_impulses(self):
        """Только импульсы — оставляем все."""
        t = datetime(2026, 1, 1)
        impulses = [
            make_pattern(t, t + timedelta(hours=10)),
            make_pattern(t + timedelta(hours=20), t + timedelta(hours=30)),
        ]
        f = OverlapFilter(impulses, [], [])
        imps, diags, corrs = f.filter()
        assert len(imps) == 2
        assert len(diags) == 0
        assert len(corrs) == 0
    
    def test_impulse_blocks_diagonal(self):
        """Импульс перекрывает диагональ — диагональ убирается."""
        t = datetime(2026, 1, 1)
        impulse = make_pattern(t, t + timedelta(hours=20))
        diagonal = make_pattern(t + timedelta(hours=5), t + timedelta(hours=25))
        
        f = OverlapFilter([impulse], [diagonal], [])
        imps, diags, corrs = f.filter()
        assert len(imps) == 1
        assert len(diags) == 0, "Диагональ должна быть убрана"
    
    def test_impulse_blocks_correction(self):
        """Импульс перекрывает коррекцию — коррекция убирается."""
        t = datetime(2026, 1, 1)
        impulse = make_pattern(t, t + timedelta(hours=20))
        correction = make_pattern(t + timedelta(hours=5), t + timedelta(hours=25))
        
        f = OverlapFilter([impulse], [], [correction])
        imps, diags, corrs = f.filter()
        assert len(imps) == 1
        assert len(corrs) == 0, "Коррекция должна быть убрана"
    
    def test_diagonal_blocks_correction(self):
        """Диагональ перекрывает коррекцию — коррекция убирается."""
        t = datetime(2026, 1, 1)
        diagonal = make_pattern(t, t + timedelta(hours=20))
        correction = make_pattern(t + timedelta(hours=5), t + timedelta(hours=25))
        
        f = OverlapFilter([], [diagonal], [correction])
        imps, diags, corrs = f.filter()
        assert len(diags) == 1
        assert len(corrs) == 0, "Коррекция должна быть убрана"
    
    def test_no_overlap_keeps_all(self):
        """Паттерны не перекрываются — все остаются."""
        t = datetime(2026, 1, 1)
        impulse = make_pattern(t, t + timedelta(hours=10))
        diagonal = make_pattern(t + timedelta(hours=20), t + timedelta(hours=30))
        correction = make_pattern(t + timedelta(hours=40), t + timedelta(hours=50))
        
        f = OverlapFilter([impulse], [diagonal], [correction])
        imps, diags, corrs = f.filter()
        assert len(imps) == 1
        assert len(diags) == 1
        assert len(corrs) == 1
    
    def test_multiple_overlaps(self):
        """Несколько наложений — фильтр убирает всё лишнее."""
        t = datetime(2026, 1, 1)
        impulses = [make_pattern(t, t + timedelta(hours=30))]
        diagonals = [
            make_pattern(t + timedelta(hours=5), t + timedelta(hours=15)),   # перекрытие
            make_pattern(t + timedelta(hours=50), t + timedelta(hours=60)),  # не перекрытие
        ]
        corrections = [
            make_pattern(t + timedelta(hours=10), t + timedelta(hours=20)),  # перекрытие
            make_pattern(t + timedelta(hours=70), t + timedelta(hours=80)),  # не перекрытие
        ]
        
        f = OverlapFilter(impulses, diagonals, corrections)
        imps, diags, corrs = f.filter()
        assert len(imps) == 1
        assert len(diags) == 1, "Должна остаться 1 диагональ (вторая не перекрывается)"
        assert len(corrs) == 1, "Должна остаться 1 коррекция (вторая не перекрывается)"
