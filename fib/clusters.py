"""
Clusters - Кластеры уровней Фибоначчи.

Кластер — зона, где сходятся 2-3 уровня от разных измерений Фибоначчи.

Правила (traderevolution.by):
- В среднем 2-3 уровня в кластере.
- Кластер может быть зоной входа или выхода.
- Нужно подтверждение разворота (дивергенция, Price Action).
- Кластеры строятся от ортодоксальных точек.
"""
import pandas as pd


class ClusterFinder:
    """Поиск кластеров уровней Фибоначчи."""
    
    def __init__(self, tolerance_pct=0.003):
        """
        Args:
            tolerance_pct: допуск для группировки уровней в кластер
                          (например, 0.001 = 10 pips для EURUSD на 1.1000)
        """
        self.tolerance_pct = tolerance_pct
        self.clusters = []
    
    def _extract_levels(self, fib_results):
        """
        Извлекает все уровни из результатов retracement/extension.
        
        Args:
            fib_results: список dict с 'levels' или 'targets'
        
        Returns:
            список (price, source, wave)
        """
        all_levels = []
        
        for r in fib_results:
            # Retracement: 'levels'
            if 'levels' in r:
                for lvl, price in r['levels'].items():
                    if price is not None and not pd.isna(price):
                        all_levels.append({
                            'price': float(price),
                            'ratio': float(lvl),
                            'wave': r.get('wave', '?'),
                            'source': 'retracement',
                        })
            
            # Extension: 'targets'
            if 'targets' in r:
                for lvl, price in r['targets'].items():
                    if price is not None and not pd.isna(price):
                        all_levels.append({
                            'price': float(price),
                            'ratio': float(lvl),
                            'wave': r.get('wave', '?'),
                            'source': 'extension',
                        })
        
        return all_levels
    
    def find_clusters(self, fib_results):
        """
        Находит кластеры — зоны, где сходятся 2+ уровня.
        
        Args:
            fib_results: список dict с 'levels' или 'targets'
        
        Returns:
            список кластеров
        """
        all_levels = self._extract_levels(fib_results)
        
        if len(all_levels) < 2:
            print(f"[INFO] Недостаточно уровней для кластеров: {len(all_levels)}")
            self.clusters = []
            return []
        
        # Сортируем по цене
        all_levels.sort(key=lambda x: x['price'])
        
        # Группируем близкие уровни
        clusters = []
        used = [False] * len(all_levels)
        
        for i, lvl in enumerate(all_levels):
            if used[i]:
                continue
            
            # Ищем все уровни в пределах tolerance
            group = [lvl]
            used[i] = True
            
            for j in range(i + 1, len(all_levels)):
                if used[j]:
                    continue
                other = all_levels[j]
                
                # Проверка близости (в процентах от цены)
                price_diff = abs(other['price'] - lvl['price'])
                tolerance = lvl['price'] * self.tolerance_pct
                
                if price_diff <= tolerance:
                    group.append(other)
                    used[j] = True
            
            # Кластер = 2+ уровня
            if len(group) >= 2:
                prices = [g['price'] for g in group]
                clusters.append({
                    'zone_low': min(prices),
                    'zone_high': max(prices),
                    'center': sum(prices) / len(prices),
                    'strength': len(group),
                    'levels': group,
                })
        
        # Сортируем по силе
        clusters.sort(key=lambda x: x['strength'], reverse=True)
        
        self.clusters = clusters
        print(f"[OK] Найдено кластеров: {len(clusters)}")
        
        for c in clusters[:5]:
            print(f"  Зона {c['zone_low']:.5f} - {c['zone_high']:.5f} "
                  f"({c['strength']} уровней)")
        
        return clusters
    
    def get_strong_clusters(self, min_strength=2):
        """Возвращает только сильные кластеры (≥ min_strength уровней)."""
        return [c for c in self.clusters if c['strength'] >= min_strength]
    
    def get_clusters(self):
        return self.clusters
