"""
Overlap Filter - Убирает наложения между паттернами разных типов.
Приоритет: Импульс > Диагональ > Коррекция.
"""
import pandas as pd


class OverlapFilter:
    """
    Фильтрует паттерны, убирая те, что перекрываются с более приоритетными.
    """
    
    def __init__(self, impulses, diagonals, corrections):
        self.impulses = impulses or []
        self.diagonals = diagonals or []
        self.corrections = corrections or []
    
    def _get_time_range(self, pattern):
        """Возвращает (start_time, end_time) паттерна."""
        points = pattern['points']
        return points[0][0], points[-1][0]
    
    def _overlaps(self, p1, p2):
        """Проверяет, перекрываются ли два паттерна по времени."""
        s1, e1 = self._get_time_range(p1)
        s2, e2 = self._get_time_range(p2)
        return (s1 < e2) and (e1 > s2)
    
    def filter(self):
        """
        Возвращает (impulses, diagonals, corrections) без наложений.
        
        Логика:
        1. Импульсы — приоритет 1 (главные). Оставляем все.
        2. Диагонали — приоритет 2. Убираем те, что перекрываются с импульсами.
        3. Коррекции — приоритет 3. Убираем те, что перекрываются с импульсами ИЛИ диагоналями.
        """
        print(f"\n[INFO] Фильтр наложений:")
        print(f"  До:  {len(self.impulses)} импульсов, {len(self.diagonals)} диагоналей, {len(self.corrections)} коррекций")
        
        # Импульсы — оставляем все
        filtered_impulses = list(self.impulses)
        
        # Диагонали — убираем перекрывающиеся с импульсами
        filtered_diagonals = []
        for d in self.diagonals:
            overlaps_impulse = any(
                self._overlaps(d, imp) for imp in filtered_impulses
            )
            if not overlaps_impulse:
                filtered_diagonals.append(d)
            else:
                print(f"   Убрана диагональ {d['start_time'].strftime('%m-%d %H:%M')} (перекрытие с импульсом)")
        
        # Коррекции — убираем перекрывающиеся с импульсами ИЛИ диагоналями
        filtered_corrections = []
        for c in self.corrections:
            overlaps_impulse = any(
                self._overlaps(c, imp) for imp in filtered_impulses
            )
            overlaps_diagonal = any(
                self._overlaps(c, d) for d in filtered_diagonals
            )
            if not overlaps_impulse and not overlaps_diagonal:
                filtered_corrections.append(c)
        
        print(f"  После: {len(filtered_impulses)} импульсов, {len(filtered_diagonals)} диагоналей, {len(filtered_corrections)} коррекций")
        
        return filtered_impulses, filtered_diagonals, filtered_corrections
