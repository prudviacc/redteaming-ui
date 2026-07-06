"""Shared UI utilities — sidebar backend status and workflow step indicator."""

import os

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

_BASE_URL = os.environ.get("AGENT_API_URL", "http://localhost:8000").rstrip("/")

_STEPS = [
    ("1", "Register Agent"),
    ("2", "Configure Attacks"),
    ("3", "Attack Details"),
    ("4", "Execution Results"),
]


@st.cache_data(ttl=30, show_spinner=False)
def _ping_backend(url: str) -> bool:
    try:
        requests.get(url, timeout=2)
        return True
    except requests.exceptions.ConnectionError:
        return False
    except Exception:
        return True


def render_sidebar(current_step: int) -> None:
    """Append backend status and workflow progress to the sidebar."""
    with st.sidebar:
        st.divider()
        st.markdown("**Backend**")
        online = _ping_backend(_BASE_URL)
        if online:
            st.success("Connected", icon="✅")
        else:
            st.error("Offline", icon="❌")
            st.caption("Set `AGENT_API_URL` in `.env`")
        st.caption(f"`{_BASE_URL}`")

        st.divider()
        st.markdown("**Workflow**")
        for i, (num, label) in enumerate(_STEPS, 1):
            if i < current_step:
                st.markdown(f"✅ {num}. {label}")
            elif i == current_step:
                st.markdown(f"**▶ {num}. {label}**")
            else:
                st.markdown(f"○ {num}. {label}")
