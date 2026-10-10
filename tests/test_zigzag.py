"""
Тесты для core.zigzag.ZigZag
"""
import pytest
import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.zigzag import ZigZag


@pytest.fixture
def simple_data():
    """Простые данные: 10 свечей с явными пивотами."""
    dates = [datetime(2026, 1, 1) + timedelta(hours=i) for i in range(20)]
    prices = [1.1000, 1.1010, 1.1020, 1.1010, 1.1000, 
              1.0990, 1.0980, 1.0990, 1.1000, 1.1010,
              1.1020, 1.1030, 1.1020, 1.1010, 1.1000,
              1.0990, 1.0980, 1.0990, 1.1000, 1.1010]
    
    df = pd.DataFrame({
        'open': prices,
        'high': [p + 0.0005 for p in prices],
        'low':  [p - 0.0005 for p in prices],
        'close': prices,
        'tick_volume': [100] * 20
    }, index=dates)
    return df


class TestZigZag:
    def test_find_pivots_basic(self, simple_data):
        """Проверяет, что пивоты находятся."""
        zz = ZigZag(simple_data, length=3)
        pivots = zz.find_pivots()
        assert pivots is not None
        assert len(pivots) >= 3, "Должно быть минимум 3 пивота"
    
    def test_pivots_alternate(self, simple_data):
        """Проверяет, что пивоты чередуются high/low."""
        zz = ZigZag(simple_data, length=3)
        pivots = zz.find_pivots()
        types = pivots['type'].values
        for i in range(len(types) - 1):
            assert types[i] != types[i + 1], "Пивоты должны чередоваться"
    
    def test_no_consecutive_same_type(self, simple_data):
        """Нет двух high или двух low подряд."""
        zz = ZigZag(simple_data, length=3)
        pivots = zz.find_pivots()
        types = pivots['type'].values
        for i in range(len(types) - 1):
            assert not (types[i] == types[i+1] == 'high'), "Два high подряд"
            assert not (types[i] == types[i+1] == 'low'), "Два low подряд"
    
    def test_zigzag_length_effect(self, simple_data):
        """Чем больше length, тем меньше пивотов."""
        zz1 = ZigZag(simple_data, length=2)
        pivots1 = zz1.find_pivots()
        
        zz2 = ZigZag(simple_data, length=5)
        pivots2 = zz2.find_pivots()
        
        assert len(pivots1) >= len(pivots2), "Больше length → меньше пивотов"
    
    def test_empty_data(self):
        """Что если данных нет?"""
        df = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'tick_volume'])
        zz = ZigZag(df, length=3)
        pivots = zz.find_pivots()
        assert len(pivots) == 0
    
    def test_one_candle(self):
        """Что если 1 свеча?"""
        df = pd.DataFrame({
            'open': [1.1000], 'high': [1.1010], 'low': [1.0990],
            'close': [1.1005], 'tick_volume': [100]
        }, index=[datetime(2026, 1, 1)])
        zz = ZigZag(df, length=3)
        pivots = zz.find_pivots()
        assert len(pivots) == 0
    
    def test_pivots_prices_valid(self, simple_data):
        """Цены пивотов совпадают с max/min данных."""
        zz = ZigZag(simple_data, length=3)
        pivots = zz.find_pivots()
        
        for time, row in pivots.iterrows():
            actual_price = row['price']
            if row['type'] == 'high':
                assert actual_price == simple_data.loc[time, 'high'], "High не совпадает"
            else:
                assert actual_price == simple_data.loc[time, 'low'], "Low не совпадает"
    
    def test_get_zigzag_line(self, simple_data):
        """Проверяет метод get_zigzag_line."""
        zz = ZigZag(simple_data, length=3)
        zz.find_pivots()
        line = zz.get_zigzag_line()
        assert 'price' in line.columns
        assert 'type' in line.columns
