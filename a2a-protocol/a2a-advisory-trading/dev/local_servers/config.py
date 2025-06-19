import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent.absolute()
AGENTS_DIR = ROOT_DIR / "iac" / "agents"

def setup_paths():
    sys.path.insert(0, str(ROOT_DIR))
    sys.path.insert(0, str(ROOT_DIR / "iac"))

    print(f"Root directory: {ROOT_DIR}")
    print(f"Python path: {sys.path}")
