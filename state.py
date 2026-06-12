"""Local state persistence to prevent duplicate alerts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BotState:
    last_signal: str | None = None


def load_state(path: str) -> BotState:
    p = Path(path)
    if not p.exists():
        return BotState(last_signal=None)

    try:
        obj: Any = json.loads(p.read_text(encoding="utf-8"))
        return BotState(last_signal=obj.get("last_signal"))
    except Exception:
        # Fail open: if state is corrupted, still allow sending.
        return BotState(last_signal=None)


def save_state(path: str, state: BotState) -> None:
    p = Path(path)
    p.write_text(json.dumps({"last_signal": state.last_signal}, ensure_ascii=False), encoding="utf-8")

