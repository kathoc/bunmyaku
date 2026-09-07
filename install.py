"""Run from an extracted release: python install.py."""
import sys
from pathlib import Path

if sys.version_info < (3, 11):
    raise SystemExit("Python 3.11以上が必要です")
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from jlangbase.distribution import main

if __name__ == "__main__":
    main()
