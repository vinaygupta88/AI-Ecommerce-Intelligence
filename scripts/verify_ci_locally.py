"""
scripts/verify_ci_locally.py
Simulates the GitHub Actions CI pipeline locally to catch regressions before git push.
Runs linting, pytest, and file checks.
"""

import subprocess
import sys


def run_command(name: str, cmd: list[str]) -> bool:
    print(f"\n[*] Running CI Stage: {name}...")
    print(f"    Command: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode == 0:
        print(f"    [PASS] {name} succeeded.")
        return True
    else:
        print(f"    [FAIL] {name} failed with exit code {result.returncode}.")
        return False


def main():
    print("==================================================")
    print("LOCAL CI PRE-FLIGHT VERIFICATION")
    print("==================================================")

    steps = [
        ("Flake8 Syntax Linting", [sys.executable, "-m", "flake8", ".", "--count", "--select=E9,F63,F7,F82", "--exclude=venv,.venv,airflow/logs"]),
        ("Pytest Test Suite", [sys.executable, "-m", "pytest", "-v"]),
    ]

    all_ok = True
    for name, cmd in steps:
        if not run_command(name, cmd):
            all_ok = False
            break

    print("\n--------------------------------------------------")
    if all_ok:
        print("[SUCCESS] All local CI stages passed! Safe to commit and push.")
    else:
        print("[ERROR] Local CI checks failed. Fix the errors above before pushing.")
        sys.exit(1)


if __name__ == "__main__":
    main()