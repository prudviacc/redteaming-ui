"""Step 1 — Select agent, configure attack categories, execution mode, and generate."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from store.profile_store import load_agents
from store.session_store import save_attacks
from utils import render_sidebar

st.set_page_config(page_title="Configure Attacks", layout="wide")
render_sidebar(2)
st.title("Configure Attacks")
st.caption("Select an agent, choose attack categories, configure execution mode, then generate.")

ATTACK_CATEGORIES = {
    "prompt_injection":   "Inject instructions that override the agent's original system prompt.",
    "goal_hijacking":     "Redirect the agent away from its intended task toward a different goal.",
    "jailbreak":          "Bypass safety guidelines using role-play, hypotheticals, or encoding tricks.",
    "data_extraction":    "Attempt to extract system prompts, internal data, or PII.",
    "role_play":          "Use fictional framing to make the agent violate its constraints.",
    "authority_override": "Impersonate administrators or developers to gain elevated permissions.",
    "context_confusion":  "Introduce conflicting context to cause the agent to behave inconsistently.",
    "logic_exploitation": "Use logical paradoxes or edge cases to confuse the agent's decision-making.",
}

# ── 1. Agent selector ──────────────────────────────────────────────────────────
st.subheader("1 — Select Agent")

agents = load_agents()
if not agents:
    st.warning("No agents registered. Go to **Home** to register an agent first.")
    st.stop()

agent_options = {f"{a['name']}  (ID: {a['agent_id'][:8]}...)": a for a in agents}
current = st.session_state.get("selected_agent", {})
default_label = next(
    (label for label, a in agent_options.items() if a.get("agent_id") == current.get("agent_id")),
    list(agent_options.keys())[0],
)

chosen_label   = st.selectbox("Agent", list(agent_options.keys()), index=list(agent_options.keys()).index(default_label))
selected_agent = agent_options[chosen_label]
st.session_state["selected_agent"] = selected_agent

with st.expander("View agent details"):
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**Name:** {selected_agent['name']}")
        st.markdown(f"**Description:** {selected_agent.get('description', '')}")
    with c2:
        st.markdown(f"**Capabilities:** {', '.join(selected_agent.get('capabilities', [])) or 'None'}")
        st.markdown(f"**Constraints:** {', '.join(selected_agent.get('constraints', [])) or 'None'}")

st.divider()

# ── 2. Quick Scan ──────────────────────────────────────────────────────────────
st.subheader("2 — Run Scan")

_QUICK_PLAN = [{"category": c, "test_cases": 2} for c in ATTACK_CATEGORIES]

quick_col, _ = st.columns([2, 3])
with quick_col:
    quick_scan = st.button(
        f"Quick Scan — all {len(ATTACK_CATEGORIES)} categories, 2 prompts each",
        type="primary",
        width='stretch',
        help="Runs all attack categories with 2 test cases each using LLM Simulation.",
    )

# ── Advanced options ───────────────────────────────────────────────────────────
with st.expander("Advanced Options — customise categories, test cases, and execution mode"):
    st.caption("Enable categories and set the number of test cases to generate for each.")

    attack_plan = []
    cols = st.columns(2)
    for idx, (category, description) in enumerate(ATTACK_CATEGORIES.items()):
        col = cols[idx % 2]
        with col:
            with st.container(border=True):
                enabled = st.checkbox(
                    f"**{category.replace('_', ' ').title()}**",
                    key=f"chk_{category}",
                )
                st.caption(description)
                if enabled:
                    test_cases = st.number_input(
                        "Test cases",
                        min_value=1,
                        max_value=10,
                        value=2,
                        key=f"num_{category}",
                    )
                    attack_plan.append({"category": category, "test_cases": int(test_cases)})

    st.divider()
    st.markdown("**Execution Mode**")

    execute = st.toggle(
        "Execute attacks after generation",
        value=False,
        help="When ON, each generated prompt is sent to the target agent and the response is captured.",
    )

    target_url     = None
    use_simulation = True
    target_config  = None
    adv_ready      = bool(attack_plan)

    if execute:
        st.markdown("**Target Agent Configuration**")
        target_type = st.radio(
            "Target type",
            ["Simulation", "Generic HTTP", "Azure AI Foundry"],
            horizontal=True,
            help=(
                "**Simulation** — LLM roleplays as the target agent, no live endpoint needed.  "
                "**Generic HTTP** — POST attack prompts to any HTTP agent endpoint.  "
                "**Azure AI Foundry** — Connect to an agent deployed in Azure AI Foundry."
            ),
        )

        if target_type == "Simulation":
            use_simulation = True
            target_config  = {"type": "simulation"}
            st.info("The LLM will simulate the target agent's responses based on the registered profile.")

        elif target_type == "Generic HTTP":
            use_simulation = False
            http_url = st.text_input(
                "Endpoint URL *",
                placeholder="https://your-agent.example.com/chat",
                help='Must accept POST with JSON body {"message": "..."}',
            )
            with st.expander("Headers & Auth (optional)"):
                headers_raw = st.text_area(
                    "Custom headers (JSON)",
                    placeholder='{"Authorization": "Bearer token123"}',
                    height=70,
                )
                auth_method = st.selectbox("Auth method", ["None", "Bearer Token", "API Key"])
                auth_value  = ""
                if auth_method != "None":
                    auth_value = st.text_input(f"{auth_method} value", type="password")

            if not http_url.strip():
                st.warning("Endpoint URL is required for Generic HTTP.")
                adv_ready = False
            else:
                target_url    = http_url.strip()
                auth_cfg      = {"mode": "none"} if auth_method == "None" else {"mode": auth_method.lower().replace(" ", "_"), "value": auth_value}
                target_config = {"type": "generic_http", "endpoint": target_url, "auth": auth_cfg}
                st.success(f"Will POST to: `{target_url}`")

        elif target_type == "Azure AI Foundry":
            use_simulation   = False
            foundry_endpoint = st.text_input(
                "Project endpoint *",
                placeholder="https://<your-project>.openai.azure.com/",
            )
            foundry_agent_id = st.text_input(
                "Agent / deployment name *",
                placeholder="my-redteam-agent",
            )
            foundry_auth = st.selectbox(
                "Auth mode",
                ["Azure CLI", "Managed Identity", "API Key"],
                help=(
                    "**Azure CLI** — uses your `az login` session.  "
                    "**Managed Identity** — for Azure-hosted environments.  "
                    "**API Key** — provide an API key directly."
                ),
            )
            foundry_api_key = ""
            if foundry_auth == "API Key":
                foundry_api_key = st.text_input("API Key", type="password")

            missing = []
            if not foundry_endpoint.strip():
                missing.append("Project endpoint")
            if not foundry_agent_id.strip():
                missing.append("Agent / deployment name")
            if foundry_auth == "API Key" and not foundry_api_key:
                missing.append("API Key")

            if missing:
                st.warning(f"Required: {', '.join(missing)}")
                adv_ready = False
            else:
                auth_cfg      = {"mode": foundry_auth.lower().replace(" ", "_")}
                if foundry_auth == "API Key":
                    auth_cfg["api_key"] = foundry_api_key
                target_config = {
                    "type":     "azure_foundry",
                    "endpoint": foundry_endpoint.strip(),
                    "agent_id": foundry_agent_id.strip(),
                    "auth":     auth_cfg,
                }
                st.success(f"Azure Foundry: `{foundry_endpoint.strip()}` — `{foundry_agent_id.strip()}`")

    total_attacks = sum(item["test_cases"] for item in attack_plan)
    if attack_plan:
        mode_label = (
            f"Simulation" if (execute and use_simulation)
            else f"Generic HTTP → {target_url}" if (execute and target_type == "Generic HTTP" and target_url)
            else f"Azure AI Foundry" if (execute and target_type == "Azure AI Foundry")
            else "generate only"
        )
        st.info(
            f"**{len(attack_plan)}** categor{'y' if len(attack_plan) == 1 else 'ies'} — "
            f"**{total_attacks}** prompt(s) — Mode: **{mode_label}**"
        )
    else:
        st.caption("Select at least one category above to enable custom scan.")

    adv_btn_label = f"{('Generate & Execute' if execute else 'Generate')} {total_attacks} Attack(s)"
    adv_scan = st.button(adv_btn_label, type="secondary", disabled=not adv_ready, width='stretch')

st.divider()

# ── Resolve which scan was triggered ──────────────────────────────────────────
if quick_scan:
    attack_plan    = _QUICK_PLAN
    execute        = True
    use_simulation = True
    target_url     = None
    target_config  = {"type": "simulation"}
    ready          = True
elif "adv_scan" in dir() and adv_scan:
    ready = adv_ready
else:
    ready = False

if quick_scan or (adv_scan and adv_ready):
    total_attacks = sum(item["test_cases"] for item in attack_plan)
    status_label = "Generating and executing attacks..." if execute else "Generating attack prompts..."

    with st.status(status_label, expanded=True) as status:
        st.write(f"Agent: **{selected_agent['name']}**")
        st.write(f"Categories: {', '.join(item['category'] for item in attack_plan)}")
        st.write(f"Total prompts: **{total_attacks}**")
        if execute and target_config:
            st.write(f"Target: **{target_config.get('type', '').replace('_', ' ').title()}**")
        try:
            from services.agent_client import generate_attacks
            output = generate_attacks(
                agent_profile=selected_agent,
                attack_plan=attack_plan,
                execute=execute,
                target_url=target_url.strip() if target_url else None,
                use_simulation=use_simulation,
                target_config=target_config,
            )
            save_attacks(
                agent_id=selected_agent.get("agent_id", ""),
                agent_name=selected_agent["name"],
                attack_output=output,
            )
            st.session_state["generated_attacks"] = output
            st.session_state["attack_agent"]      = selected_agent

            generated = output["total_generated"]
            executed  = output.get("total_executed", 0)
            done_msg  = (
                f"Done — {generated} prompt(s) generated, {executed} executed."
                if execute else
                f"Done — {generated} prompt(s) generated."
            )
            status.update(label=done_msg, state="complete", expanded=False)
        except Exception as e:
            status.update(label="Failed", state="error")
            msg = str(e)
            if "Cannot reach" in msg or "Expecting value" in msg or "ConnectionError" in msg:
                st.error("Backend is offline — check the sidebar for connection status and verify `AGENT_API_URL` in `.env`.")
            else:
                st.error(f"Error: {msg}")
            st.stop()

    st.switch_page("pages/2_Attack_Details.py")
