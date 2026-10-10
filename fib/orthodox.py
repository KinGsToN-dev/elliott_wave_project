"""
Orthodox - Ортодоксальные точки для всех паттернов.

Правила (traderevolution.by):
- Ортодоксальные точки — истинные окончания волн.
- НЕ совпадают с локальными max/min.
- Определяют общее окончание модели.
- Встречаются в: импульсах (усечение), плоскостях,
  треугольниках, конечных диагоналях, комбинациях.
"""
import pandas as pd


class OrthodoxPointsDetector:
    """Определение ортодоксальных точек для паттернов."""
    
    def __init__(self):
        self.points = []
    
    # ============================================================
    # ИМПУЛЬСЫ
    # ============================================================
    def get_orthodox_impulse(self, impulse):
        """
        Для импульса с усечением (Truncated 5th):
        ортодоксальная точка = окончание W3.
        Иначе — окончание W5.
        """
        points = impulse['points']
        
        if impulse.get('truncated') and len(points) >= 4:
            # W3 = points[3]
            return points[3][0], points[3][1]
        
        return points[-1][0], points[-1][1]
    
    # ============================================================
    # ПЛОСКОСТИ
    # ============================================================
    def get_orthodox_flat(self, flat):
        """
        Для плоскости: если W_C — усечение (running flat),
        ортодоксальная точка = окончание W_A.
        Иначе — окончание W_C.
        """
        points = flat['points']
        subtype = flat.get('subtype', 'regular')
        
        if subtype == 'running' and len(points) >= 3:
            # Ортодоксальная = окончание W_A (points[1])
            return points[1][0], points[1][1]
        
        return points[-1][0], points[-1][1]
    
    # ============================================================
    # ТРЕУГОЛЬНИКИ
    # ============================================================
    def get_orthodox_triangle(self, triangle):
        """
        Для треугольника: ортодоксальная точка = окончание волны E.
        Для бегущего — окончание D.
        """
        points = triangle['points']
        subtype = triangle.get('subtype', 'symmetric')
        
        if subtype == 'running' and len(points) >= 5:
            return points[-2][0], points[-2][1]
        
        return points[-1][0], points[-1][1]
    
    # ============================================================
    # ДИАГОНАЛИ
    # ============================================================
    def get_orthodox_diagonal(self, diagonal):
        """
        Для конечной диагонали с усечением:
        ортодоксальная точка = окончание W3.
        Иначе — окончание W5.
        """
        points = diagonal['points']
        
        if diagonal.get('truncated') and len(points) >= 4:
            return points[3][0], points[3][1]
        
        return points[-1][0], points[-1][1]
    
    # ============================================================
    # КОМБИНАЦИИ
    # ============================================================
    def get_orthodox_combination(self, combination):
        """
        Для комбинации: ортодоксальная точка = окончание последней волны (Z).
        """
        points = combination['points']
        return points[-1][0], points[-1][1]
    
    # ============================================================
    # УНИВЕРСАЛЬНЫЙ МЕТОД
    # ============================================================
    def get_orthodox_end(self, pattern):
        """
        Универсальный метод — определяет ортодоксальную точку
        в зависимости от типа паттерна.
        """
        ptype = pattern.get('type', '')
        
        if ptype == 'impulse' or ('truncated' in pattern and 'points' in pattern and len(pattern['points']) == 6):
            return self.get_orthodox_impulse(pattern)
        elif ptype in ['flat', 'zigzag']:
            if ptype == 'flat':
                return self.get_orthodox_flat(pattern)
            return pattern['points'][-1][0], pattern['points'][-1][1]
        elif ptype == 'triangle':
            return self.get_orthodox_triangle(pattern)
        elif ptype in ['diagonal', 'leading_diagonal', 'ending_diagonal']:
            return self.get_orthodox_diagonal(pattern)
        elif ptype in ['double_three', 'triple_three']:
            return self.get_orthodox_combination(pattern)
        else:
            # По умолчанию — последняя точка
            if 'points' in pattern and pattern['points']:
                return pattern['points'][-1][0], pattern['points'][-1][1]
        
        return None, None
    
    def get_orthodox_start(self, pattern):
        """Ортодоксальная точка начала — обычно первая точка."""
        if 'points' in pattern and pattern['points']:
            return pattern['points'][0][0], pattern['points'][0][1]
        return None, None
    
    def adjust_pattern(self, pattern):
        """Добавляет orthodox_start/orthodox_end к паттерну."""
        if not pattern.get('points'):
            return pattern
        
        start_time, start_price = self.get_orthodox_start(pattern)
        end_time, end_price = self.get_orthodox_end(pattern)
        
        adjusted = dict(pattern)
        adjusted['orthodox_start'] = (start_time, start_price)
        adjusted['orthodox_end'] = (end_time, end_price)
        adjusted['is_truncated'] = bool(pattern.get('truncated', False))
        
        return adjusted
    
    def find_all_orthodox(self, patterns):
        """Обрабатывает список паттернов."""
        self.points = []
        adjusted = []
        
        for p in patterns:
            adj = self.adjust_pattern(p)
            adjusted.append(adj)
            self.points.append({
                'pattern_id': id(p),
                'type': p.get('type', 'unknown'),
                'start': adj['orthodox_start'],
                'end': adj['orthodox_end'],
                'is_truncated': adj['is_truncated'],
            })
        
        return adjusted
    
    def get_points(self):
        return self.points
