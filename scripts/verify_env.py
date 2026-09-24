"""
scripts/verify_env.py
Validates the developer workstation environment, dependencies, and file structure.
"""

import sys
import os
import shutil
import importlib

# Critical dependencies to test
REQUIRED_PACKAGES = [
    "numpy",
    "pandas",
    "sklearn",
    "lightgbm",
    "xgboost",
    "fastapi",
    "uvicorn",
    "pydantic",
    "sqlalchemy",
    "redis",
    "jose",
    "passlib",
    "mlflow",
    "evidently",
    "pytest",
]

REQUIRED_DIRS = [
    "backend/app",
    "frontend",
    "ml/data/raw",
    "ml/data/processed",
    "ml/features",
    "ml/training",
    "ml/inference",
    "ml/evaluation",
    "pipelines",
    "monitoring",
    "tests/unit",
    "tests/integration",
    "scripts",
]


def check_python_version() -> bool:
    print(f"[*] Checking Python version... Found: {sys.version.split()[0]}")
    if sys.version_info < (3, 10):
        print("[FAIL] Python 3.10+ is required.")
        return False
    print("[PASS] Python version compatible.")
    return True


def check_packages() -> bool:
    print("\n[*] Checking installed packages...")
    all_ok = True
    for pkg in REQUIRED_PACKAGES:
        try:
            importlib.import_module(pkg)
            print(f"  [OK] {pkg}")
        except ImportError as e:
            print(f"  [FAIL] Missing package: {pkg} ({e})")
            all_ok = False
    return all_ok


def check_directories() -> bool:
    print("\n[*] Checking directory structure...")
    all_ok = True
    for d in REQUIRED_DIRS:
        if os.path.isdir(d):
            print(f"  [OK] {d}/")
        else:
            print(f"  [FAIL] Directory missing: {d}/")
            all_ok = False
    return all_ok


def check_external_tools():
    print("\n[*] Checking external CLI tools...")
    tools = {
        "git": "Version control",
        "docker": "Container orchestration",
        "node": "Frontend runtime (Node.js)",
        "npm": "Node package manager",
    }
    for tool, desc in tools.items():
        path = shutil.which(tool)
        if path:
            print(f"  [OK] {tool} ({desc}) -> {path}")
        else:
            print(f"  [WARN] {tool} ({desc}) NOT found in system PATH. (Required in later phases)")


def check_env_file() -> bool:
    print("\n[*] Checking environment files...")
    if not os.path.isfile(".env.example"):
        print("  [FAIL] .env.example missing.")
        return False
    if not os.path.isfile(".env"):
        print("  [WARN] .env not found. Copying from .env.example...")
        shutil.copy(".env.example", ".env")
    print("  [OK] .env configuration present.")
    return True


if __name__ == "__main__":
    print("==================================================")
    print("AI SUPPLY CHAIN PLATFORM: ENVIRONMENT VERIFICATION")
    print("==================================================")

    py_ok = check_python_version()
    env_ok = check_env_file()
    dirs_ok = check_directories()
    pkgs_ok = check_packages()
    check_external_tools()

    print("\n--------------------------------------------------")
    if py_ok and env_ok and dirs_ok and pkgs_ok:
        print("[SUCCESS] All core checks passed! Environment is ready for Phase 2.")
        sys.exit(0)
    else:
        print("[ERROR] Environment setup incomplete. Review failed checks above.")
        sys.exit(1)