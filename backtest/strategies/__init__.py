"""
Strategies - Реестр всех стратегий.
"""
from .base import BaseStrategy
from .w2_w3 import W2W3Strategy


# Реестр стратегий: имя → класс
STRATEGIES = {
    'w2_w3': W2W3Strategy,
}


def get_strategy(name):
    """Возвращает класс стратегии по имени."""
    if name not in STRATEGIES:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(STRATEGIES.keys())}")
    return STRATEGIES[name]


def list_strategies():
    """Возвращает список доступных стратегий."""
    return list(STRATEGIES.keys())
