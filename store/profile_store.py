"""Persistent agent profile registry — backed by storage/profiles.json."""

import json
import os
import uuid
from datetime import datetime
from typing import Optional

_UI_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STORAGE_DIR = os.path.join(_UI_ROOT, "storage")
_PROFILES_FILE = os.path.join(_STORAGE_DIR, "profiles.json")


def register_agent(profile_data: dict) -> str:
    """Save a new agent and return its generated agent_id."""
    agents = load_agents()
    agent_id = str(uuid.uuid4())
    entry = {
        **profile_data,
        "agent_id": agent_id,
        "registered_at": datetime.now().isoformat(),
    }
    agents.append(entry)
    _write(agents)
    return agent_id


def load_agents() -> list:
    if not os.path.exists(_PROFILES_FILE):
        return []
    try:
        with open(_PROFILES_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def get_agent(agent_id: str) -> Optional[dict]:
    return next((a for a in load_agents() if a.get("agent_id") == agent_id), None)


def update_agent(agent_id: str, profile_data: dict) -> bool:
    agents = load_agents()
    for i, a in enumerate(agents):
        if a.get("agent_id") == agent_id:
            agents[i] = {
                **profile_data,
                "agent_id": agent_id,
                "registered_at": a.get("registered_at", ""),
                "updated_at": datetime.now().isoformat(),
            }
            _write(agents)
            return True
    return False


def delete_agent(agent_id: str) -> bool:
    agents = load_agents()
    filtered = [a for a in agents if a.get("agent_id") != agent_id]
    if len(filtered) == len(agents):
        return False
    _write(filtered)
    return True


def _write(agents: list) -> None:
    os.makedirs(_STORAGE_DIR, exist_ok=True)
    with open(_PROFILES_FILE, "w") as f:
        json.dump(agents, f, indent=2)
