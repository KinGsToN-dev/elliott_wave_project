"""
BaseStrategy - Абстрактный класс для всех стратегий.

Все стратегии наследуются от этого класса и реализуют
метод generate_signals(). Движок работает с любыми стратегиями
через единый интерфейс.
"""
from abc import ABC, abstractmethod


class BaseStrategy(ABC):
    """Абстрактный класс для всех стратегий."""
    
    def __init__(self, name="Base"):
        self.name = name
        self.description = ""
    
    @abstractmethod
    def generate_signals(self, df, impulses, diagonals, corrections, combinations):
        """
        Генерирует список сигналов (сделок) из найденных паттернов.
        
        Args:
            df: DataFrame со свечами
            impulses: список импульсов
            diagonals: список диагоналей
            corrections: список коррекций
            combinations: список комбинаций
        
        Returns:
            Список dict с ключами:
            - entry_time: время входа
            - entry_price: цена входа
            - direction: 'BUY' / 'SELL'
            - target: цена цели (Take Profit)
            - stop: цена стопа (Stop Loss)
            - pattern: название сигнала
            - source: исходный паттерн
        """
        pass
    
    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.name}>"
