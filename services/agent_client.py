"""
Decoupling layer between the UI and the red-teaming agent.

This is the ONLY file in the UI that communicates with redteaming_ai_agent.
The agent is now a remote HTTP service (FastAPI). Set AGENT_API_URL in .env
to point at the Azure-hosted URL (or http://localhost:8000 for local dev).
"""

import os
from typing import Optional

import requests
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv

load_dotenv()

_BASE_URL = os.environ.get("AGENT_API_URL", "http://localhost:8000").rstrip("/")

_TIMEOUT = int(os.environ.get("AGENT_API_TIMEOUT", "300"))

# Only initialise Azure auth when the URL points at Azure (not localhost).
_azure_token_provider = None
if not _BASE_URL.startswith("http://localhost") and not _BASE_URL.startswith("http://127."):
    _credential = DefaultAzureCredential()
    _azure_token_provider = get_bearer_token_provider(
        _credential, "https://ai.azure.com/.default"
    )


def _post(path: str, payload: dict) -> dict:
    url = f"{_BASE_URL}{path}"
    headers: dict = {}
    if _azure_token_provider:
        headers["Authorization"] = f"Bearer {_azure_token_provider()}"
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            f"Cannot reach the agent at {_BASE_URL}. "
            "Check AGENT_API_URL in .env and that the agent service is running."
        )
    except requests.exceptions.HTTPError as exc:
        detail = exc.response.json().get("detail", exc.response.text)
        raise RuntimeError(f"Agent API error ({exc.response.status_code}): {detail}")


def generate_attacks(
    agent_profile: dict,
    attack_plan: list[dict],
    execute: bool = False,
    target_url: Optional[str] = None,
    use_simulation: bool = True,
    target_config: Optional[dict] = None,
) -> dict:
    """
    Ask the agent to generate attack prompts (and optionally execute them).

    Returns:
        {"results": [...], "total_generated": int, "total_executed": int}
    """
    payload = {
        "agent_profile":  agent_profile,
        "attack_plan":    attack_plan,
        "execute":        execute,
        "target_url":     target_url,
        "use_simulation": use_simulation,
    }
    if target_config:
        payload["target"] = target_config
    return _post("/generate", payload)


def execute_attacks(
    existing_results: list[dict],
    agent_profile: dict,
    use_simulation: bool = True,
    target_url: Optional[str] = None,
    target_config: Optional[dict] = None,
) -> dict:
    """
    Execute a set of already-generated (unexecuted) attack prompts.

    Returns:
        {"results": [...], "total_generated": int, "total_executed": int}
    """
    payload = {
        "agent_profile":    agent_profile,
        "existing_results": existing_results,
        "target_url":       target_url,
        "use_simulation":   use_simulation,
    }
    if target_config:
        payload["target"] = target_config
    return _post("/execute", payload)
