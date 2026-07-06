"""Home — Register and manage target agents."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from store.profile_store import (
    delete_agent,
    get_agent,
    load_agents,
    register_agent,
    update_agent,
)
from store.session_store import load_sessions
from utils import render_sidebar

st.set_page_config(page_title="Red-Teaming AI Agent", layout="wide", initial_sidebar_state="expanded")
render_sidebar(1)

st.title("Red-Teaming AI Agent")
st.caption("Automated adversarial testing for AI agents. Register your target agent, configure attacks, and review results.")

st.divider()

agents = load_agents()
sessions = load_sessions()

# ── Metrics ───────────────────────────────────────────────────────────────────
c1, c2 = st.columns(2)
c1.metric("Registered Agents", len(agents))
c2.metric("Sessions Run", len(sessions))

st.divider()

# ── Registered agents list ─────────────────────────────────────────────────────
st.subheader("Registered Agents")

if not agents:
    st.info("No agents registered yet — use the form below to register your first agent.")
else:
    for agent in agents:
        agent_id    = agent.get("agent_id", "")
        name        = agent.get("name", "Unnamed")
        description = agent.get("description", "")
        caps        = agent.get("capabilities", [])
        cons        = agent.get("constraints", [])
        registered  = agent.get("registered_at", "")[:10]

        with st.container(border=True):
            col_info, col_actions = st.columns([5, 2])

            with col_info:
                st.markdown(f"### {name}")
                st.caption(f"ID: `{agent_id[:8]}...`  |  Registered: {registered}")
                st.markdown(description[:200] + ("..." if len(description) > 200 else ""))
                ca, cb = st.columns(2)
                with ca:
                    st.caption(f"**Capabilities:** {', '.join(caps) or 'None'}")
                with cb:
                    st.caption(f"**Constraints:** {', '.join(cons) or 'None'}")

            with col_actions:
                st.markdown("&nbsp;", unsafe_allow_html=True)
                if st.button("Select & Configure Attacks", key=f"sel_{agent_id}", type="primary", width='stretch'):
                    st.session_state["selected_agent"] = agent
                    st.switch_page("pages/1_Configure_Attacks.py")

                export_data = {k: v for k, v in agent.items() if k not in ("registered_at", "updated_at")}
                st.download_button(
                    "Export JSON",
                    data=json.dumps(export_data, indent=2),
                    file_name=f"{name.lower().replace(' ', '_')}_profile.json",
                    mime="application/json",
                    key=f"export_{agent_id}",
                    width='stretch',
                )

                if st.button("Edit", key=f"edit_{agent_id}", width='stretch'):
                    st.session_state["editing_agent_id"] = agent_id
                    st.rerun()

                with st.popover("Delete", width='stretch'):
                    st.warning(f"Delete **{name}**? This cannot be undone.")
                    if st.button("Confirm Delete", key=f"del_confirm_{agent_id}", type="secondary"):
                        delete_agent(agent_id)
                        if st.session_state.get("selected_agent", {}).get("agent_id") == agent_id:
                            st.session_state.pop("selected_agent", None)
                        st.rerun()

st.divider()

# ── Register / Edit form ───────────────────────────────────────────────────────
editing_id = st.session_state.get("editing_agent_id")
existing: dict = {}

if editing_id:
    existing = get_agent(editing_id) or {}
    st.subheader(f"Edit Agent: {existing.get('name', '')}")
    if st.button("Cancel Edit"):
        st.session_state.pop("editing_agent_id", None)
        st.rerun()
else:
    st.subheader("Register New Agent")

    # Dynamic key resets the uploader widget after a successful registration
    upload_key = st.session_state.get("upload_key", 0)
    uploaded = st.file_uploader(
        "Load from JSON (optional — pre-fills the form below)",
        type="json",
        key=f"uploader_{upload_key}",
        help="Upload an exported agent profile to pre-fill the registration form.",
    )
    if uploaded:
        try:
            data = json.load(uploaded)
            for key in ("agent_id", "registered_at", "updated_at"):
                data.pop(key, None)
            st.session_state["form_prefill"] = data
            st.success("Profile loaded — review and click Register Agent.")
        except Exception as e:
            st.error(f"Failed to parse JSON: {e}")

    existing = st.session_state.get("form_prefill", existing)

with st.form("agent_form", clear_on_submit=not editing_id):
    name = st.text_input(
        "Agent Name *",
        value=existing.get("name", ""),
        placeholder="e.g. Customer Support Bot",
    )
    description = st.text_area(
        "Description *",
        value=existing.get("description", ""),
        placeholder="What does this agent do? What is its scope?",
        height=100,
    )

    col1, col2 = st.columns(2)
    with col1:
        capabilities = st.text_input(
            "Capabilities (comma-separated)",
            value=", ".join(existing.get("capabilities", [])),
            placeholder="answer_faq, raise_ticket, check_balance",
        )
    with col2:
        constraints = st.text_input(
            "Constraints (comma-separated)",
            value=", ".join(existing.get("constraints", [])),
            placeholder="no_financial_advice, no_pii_disclosure",
        )

    btn_label = "Update Agent" if editing_id else "Register Agent"
    submitted = st.form_submit_button(btn_label, type="primary", width='stretch')

if submitted:
    if not name.strip() or not description.strip():
        st.error("Agent Name and Description are required.")
    else:
        profile_data = {
            "name":         name.strip(),
            "description":  description.strip(),
            "capabilities": [c.strip() for c in capabilities.split(",") if c.strip()],
            "constraints":  [c.strip() for c in constraints.split(",") if c.strip()],
        }
        if editing_id:
            update_agent(editing_id, profile_data)
            st.session_state.pop("editing_agent_id", None)
            st.success(f"Agent **{name.strip()}** updated.")
        else:
            new_id = register_agent(profile_data)
            profile_data["agent_id"] = new_id
            st.session_state["selected_agent"] = profile_data
            # Reset the form: clear prefill data and bump uploader key
            st.session_state.pop("form_prefill", None)
            st.session_state["upload_key"] = st.session_state.get("upload_key", 0) + 1
            st.success(f"Agent **{name.strip()}** registered — ID: `{new_id[:8]}...`")

        st.rerun()
