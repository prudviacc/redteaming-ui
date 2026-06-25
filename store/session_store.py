"""Persistent attack session store — backed by storage/attacks.json."""

import json
import os
from datetime import datetime

_UI_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STORAGE_DIR = os.path.join(_UI_ROOT, "storage")
_ATTACKS_FILE = os.path.join(_STORAGE_DIR, "attacks.json")


def save_attacks(agent_id: str, agent_name: str, attack_output: dict) -> None:
    """Append a generated attack session to history."""
    sessions = load_sessions()
    entry = {
        "agent_id":   agent_id,
        "agent_name": agent_name,
        "timestamp":  datetime.now().isoformat(),
        **attack_output,
    }
    sessions.append(entry)
    os.makedirs(_STORAGE_DIR, exist_ok=True)
    with open(_ATTACKS_FILE, "w") as f:
        json.dump(sessions, f, indent=2)


def load_sessions() -> list:
    if not os.path.exists(_ATTACKS_FILE):
        return []
    try:
        with open(_ATTACKS_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def clear_sessions() -> None:
    if os.path.exists(_ATTACKS_FILE):
        os.remove(_ATTACKS_FILE)
