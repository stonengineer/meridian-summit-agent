""" Defines DEFAULT_DIR for use by other functions"""

from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
DATA_DIR = PACKAGE_ROOT.parent / "data"