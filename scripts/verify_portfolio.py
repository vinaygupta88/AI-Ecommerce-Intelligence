import os

REQUIRED_FILES = [
    "README.md",
    "docs/deployment.md",
    "docs/eda_report.md",
    "docs/test_evaluation_report.md",
    "docker-compose.yml",
    "docker-compose.prod.yml",
    ".github/workflows/ci.yml",
]


def main():
    print("==================================================")
    print("PORTFOLIO ASSET COMPLETENESS CHECK")
    print("==================================================")

    missing = []
    for f in REQUIRED_FILES:
        if os.path.isfile(f):
            size_kb = os.path.getsize(f) / 1024
            print(f"  [OK] {f:<32} ({size_kb:.1f} KB)")
        else:
            print(f"  [MISSING] {f}")
            missing.append(f)

    print("\n--------------------------------------------------")
    if not missing:
        print("[SUCCESS] All portfolio documentation, architectural guides, and assets are complete!")
        print("Your project is ready to showcase on GitHub and resume profiles.")
    else:
        print(f"[FAIL] Missing {len(missing)} required portfolio file(s).")
        exit(1)
    print("--------------------------------------------------")


if __name__ == "__main__":
    main()