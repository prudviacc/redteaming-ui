"""Step 1 — Select agent, configure attack categories, execution mode, and generate."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from store.profile_store import load_agents
from store.session_store import save_attacks

st.set_page_config(page_title="Configure Attacks", layout="wide")
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

# ── 2. Attack categories ───────────────────────────────────────────────────────
st.subheader("2 — Configure Attack Categories")
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

# ── 3. Execution mode ──────────────────────────────────────────────────────────
st.subheader("3 — Execution Mode")

execute = st.toggle(
    "Execute attacks after generation",
    value=False,
    help="When ON, each generated prompt is sent to the target agent and the response is captured.",
)

target_url    = None
use_simulation = True
ready          = bool(attack_plan)

if execute:
    mode = st.radio(
        "Target mode",
        ["LLM Simulation", "Real Endpoint"],
        horizontal=True,
        help=(
            "**LLM Simulation** — the LLM roleplays as the target agent (no live endpoint needed).  "
            "**Real Endpoint** — prompts are HTTP-POSTed to a real agent URL."
        ),
    )
    use_simulation = (mode == "LLM Simulation")

    if use_simulation:
        st.info("The LLM will simulate the target agent's responses based on the registered profile.")
    else:
        target_url = st.text_input(
            "Target Agent URL *",
            placeholder="https://your-agent-endpoint.example.com/chat",
            help="Must accept POST with JSON body {\"message\": \"...\"}",
        )
        if not target_url.strip():
            st.warning("Target URL is required for Real Endpoint mode.")
            ready = False
        else:
            st.success(f"Will POST to: `{target_url.strip()}`")

st.divider()

# ── Summary + action button ────────────────────────────────────────────────────
total_attacks = sum(item["test_cases"] for item in attack_plan)

if attack_plan:
    action = "Generate & Execute" if execute else "Generate"
    mode_label = (
        "LLM Simulation" if (execute and use_simulation)
        else f"Real Endpoint → {target_url}" if (execute and target_url)
        else "generate only"
    )
    st.info(
        f"**{len(attack_plan)}** categor{'y' if len(attack_plan) == 1 else 'ies'} — "
        f"**{total_attacks}** prompt(s) — Mode: **{mode_label}**"
    )
else:
    st.warning("Select at least one attack category to continue.")

btn_label = f"{('Generate & Execute' if execute else 'Generate')} {total_attacks} Attack(s)"

if st.button(btn_label, type="primary", disabled=not ready, use_container_width=True):
    status_label = "Generating and executing attacks..." if execute else "Generating attack prompts..."

    with st.status(status_label, expanded=True) as status:
        st.write(f"Agent: **{selected_agent['name']}**")
        st.write(f"Categories: {', '.join(item['category'] for item in attack_plan)}")
        st.write(f"Total prompts: **{total_attacks}**")
        if execute:
            st.write(f"Execution: **{'LLM Simulation' if use_simulation else target_url}**")
        try:
            from services.agent_client import generate_attacks
            output = generate_attacks(
                agent_profile=selected_agent,
                attack_plan=attack_plan,
                execute=execute,
                target_url=target_url.strip() if target_url else None,
                use_simulation=use_simulation,
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
            st.error(f"Error: {e}")
            st.stop()

    st.switch_page("pages/2_Attack_Details.py")
