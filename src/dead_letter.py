"""Armazenamento local e auditavel de itens irrecuperaveis."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class DeadLetterStore:
    def __init__(self, path):
        self.path = Path(path)

    def register(self, *, pipeline_id: str, item: dict, reason: str) -> dict:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pipeline_id": pipeline_id,
            "reason": reason,
            "item": item,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
        return entry
