import os
import sys
from pathlib import Path

# Ensure the repository root is on sys.path so tests can import the `backend` package
# backend/tests/conftest.py -> repo root is two parents up
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Set lightweight environment for tests to avoid heavy external deps or network
# Use local sqlite DB in backend/data/dev_test.db to avoid requiring Postgres
os.environ.setdefault("DATABASE_URL", "sqlite:///./backend/data/dev_test.db")
# Use local storage backend
os.environ.setdefault("STORAGE_BACKEND", "local")
# Ensure DATA_ROOT points to backend/data so tests write into the repo data folder
os.environ.setdefault("DATA_ROOT", str(REPO_ROOT / "backend" / "data"))
