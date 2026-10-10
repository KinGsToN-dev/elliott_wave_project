"""
Strategies - Реестр всех стратегий.
"""
from .base import BaseStrategy
from .w2_w3 import W2W3Strategy
from .w4_w5 import W4W5Strategy
from .wc_reversal import WCReversalStrategy


STRATEGIES = {
    'w2_w3': W2W3Strategy,
    'w4_w5': W4W5Strategy,
    'wc_reversal': WCReversalStrategy,
}


def get_strategy(name):
    if name not in STRATEGIES:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(STRATEGIES.keys())}")
    return STRATEGIES[name]


def list_strategies():
    return list(STRATEGIES.keys())
