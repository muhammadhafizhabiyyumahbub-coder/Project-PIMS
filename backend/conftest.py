"""Root-level conftest: ensures `tests.helpers` is importable from any CWD.

When pytest runs from the repo root, `backend/` is not on sys.path, so
`from tests.conftest import ...` fails. This conftest adds `backend/` to
sys.path so test modules can import helpers via a neutral path.
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
