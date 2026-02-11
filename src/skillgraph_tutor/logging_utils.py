from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def log_trace(path: str | Path, payload: dict) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    enriched = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(enriched) + "\n")
