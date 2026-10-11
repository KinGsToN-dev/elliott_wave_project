"""
Запуск всех тестов проекта.
"""
import subprocess
import sys
import os


def run_tests():
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "--tb=short",
        "--cov=core",
        "--cov=patterns",
        "--cov=fib",
        "--cov=rules",
        "--cov=mtf",
        "--cov=backtest",
        "--cov=live",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
    ]
    
    print("=" * 60)
    print(" Elliott Wave Project - Test Suite")
    print("=" * 60)
    print()
    
    result = subprocess.run(cmd, cwd=project_root)
    
    print()
    print("=" * 60)
    if result.returncode == 0:
        print(" ✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    else:
        print(" ❌ ЕСТЬ ПАДАЮЩИЕ ТЕСТЫ!")
    print("=" * 60)
    
    return result.returncode


if __name__ == "__main__":
    sys.exit(run_tests())
