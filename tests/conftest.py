import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///./data/test_aetherforge.db")
Path("data").mkdir(exist_ok=True)
