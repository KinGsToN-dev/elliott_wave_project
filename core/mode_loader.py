"""
Mode Loader - Загрузка профилей режимов из config/modes.yaml.
"""
import yaml
import os


MODES_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'config', 'modes.yaml'
)


def load_modes():
    """Загружает все режимы из YAML."""
    if not os.path.exists(MODES_FILE):
        raise FileNotFoundError(f"Файл не найден: {MODES_FILE}")
    
    with open(MODES_FILE, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def get_mode(mode_name):
    """Возвращает настройки режима по имени."""
    modes = load_modes()
    if mode_name not in modes:
        raise ValueError(f"Unknown mode: {mode_name}. Available: {list(modes.keys())}")
    return modes[mode_name]


def list_modes():
    """Список доступных режимов."""
    return list(load_modes().keys())


if __name__ == "__main__":
    # Тестовый запуск
    print("Доступные режимы:")
    for name in list_modes():
        mode = get_mode(name)
        print(f"  {name}: {mode['name']}")
        print(f"    ТФ: {mode['timeframes']}")
        print(f"    MTF-фильтр: {mode.get('use_mtf_filter', False)}")
