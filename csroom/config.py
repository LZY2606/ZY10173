import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = Path(os.environ.get("CSROOM_DB", str(BASE_DIR / "csroom.db")))

# 24-bit cycle counter: wrap only from the highest 10% down into the lowest 10%.
COUNTER_MOD = 1 << 24
COUNTER_HIGH = 0.9 * COUNTER_MOD
COUNTER_LOW = 0.1 * COUNTER_MOD

GENESIS_HASH = "0" * 64
