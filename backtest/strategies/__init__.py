"""
Strategies - Реестр всех стратегий.
"""
from .base import BaseStrategy
from .w2_w3 import W2W3Strategy
from .w4_w5 import W4W5Strategy
from .wc_reversal import WCReversalStrategy
from .w5_divergence import W5DivergenceStrategy
from .mtf_confirmed import MTFConfirmedStrategy
from .combined import CombinedStrategy
from .wyckoff_spring import WyckoffSpringStrategy
from .wyckoff_sos import WyckoffSOSStrategy
from .wyckoff_utad import WyckoffUTADStrategy
from .wyckoff_sow import WyckoffSOWStrategy
from .wyckoff_combined import WyckoffCombinedStrategy


STRATEGIES = {
    'w2_w3': W2W3Strategy,
    'w4_w5': W4W5Strategy,
    'wc_reversal': WCReversalStrategy,
    'w5_divergence': W5DivergenceStrategy,
    'mtf_confirmed': MTFConfirmedStrategy,
    'combined': CombinedStrategy,
    'wyckoff_spring': WyckoffSpringStrategy,
    'wyckoff_sos': WyckoffSOSStrategy,
    'wyckoff_utad': WyckoffUTADStrategy,
    'wyckoff_sow': WyckoffSOWStrategy,
    'wyckoff_combined': WyckoffCombinedStrategy,
}


def get_strategy(name):
    if name not in STRATEGIES:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(STRATEGIES.keys())}")
    return STRATEGIES[name]


def list_strategies():
    return list(STRATEGIES.keys())
