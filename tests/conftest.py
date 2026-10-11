"""
Conftest - общие фикстуры для всех тестов.

Сбрасывает Singleton SignalState перед каждым тестом,
чтобы тесты были изолированы друг от друга.
"""
import pytest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from live.state import SignalState


@pytest.fixture(autouse=True)
def reset_signal_state():
    """Сбрасывает Singleton SignalState перед каждым тестом."""
    SignalState._instance = None
    yield
    SignalState._instance = None