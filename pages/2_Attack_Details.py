"""Step 2 — View generated attack prompts, rationale, and execute pending attacks."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

st.set_page_config(page_title="Attack Details", layout="wide")
st.title("Attack Details")
st.caption("Review each generated attack prompt, the rationale, and — where executed — the target agent's response.")

output = st.session_state.get("generated_attacks")
agent  = st.session_state.get("attack_agent", {})

if not output:
    st.info("No attacks generated yet. Go to **Configure Attacks** to generate prompts.")
    st.stop()

results        = output.get("results", [])
total          = output.get("total_generated", len(results))
total_executed = output.get("total_executed", 0)
was_executed   = total_executed > 0

# ── Metrics ────────────────────────────────────────────────────────────────────
categories_used = sorted({r["attack_category"] for r in results})

c1, c2, c3, c4 = st.columns(4)
c1.metric("Target Agent",      agent.get("name", "—"))
c2.metric("Prompts Generated", total)
c3.metric("Attacks Executed",  total_executed)
c4.metric("Categories Tested", len(categories_used))

if was_executed:
    st.success(f"Attacks were executed — {total_executed} response(s) captured below.")
else:
    st.info("Attacks were generated only. Enable **Execute attacks** in Configure Attacks to capture responses.")

st.divider()

# ── Filter ─────────────────────────────────────────────────────────────────────
col_filter, col_exec_filter = st.columns([3, 1])

with col_filter:
    filter_options = ["All Categories"] + [c.replace("_", " ").title() for c in categories_used]
    filter_label   = st.selectbox("Filter by category", filter_options)

with col_exec_filter:
    if was_executed:
        exec_filter = st.selectbox("Execution", ["All", "Executed", "Not Executed"])
    else:
        exec_filter = "All"

filtered = results
if filter_label != "All Categories":
    raw_cat  = filter_label.lower().replace(" ", "_")
    filtered = [r for r in filtered if r["attack_category"] == raw_cat]
if exec_filter == "Executed":
    filtered = [r for r in filtered if r.get("executed")]
elif exec_filter == "Not Executed":
    filtered = [r for r in filtered if not r.get("executed")]

st.caption(f"Showing **{len(filtered)}** of **{total}** attack(s).")

st.divider()

# ── Attack cards ───────────────────────────────────────────────────────────────
CATEGORY_COLOURS = {
    "prompt_injection":   "🔴",
    "goal_hijacking":     "🟠",
    "jailbreak":          "🔴",
    "data_extraction":    "🔴",
    "role_play":          "🟡",
    "authority_override": "🟠",
    "context_confusion":  "🟡",
    "logic_exploitation": "🟡",
}

for i, result in enumerate(filtered, 1):
    category        = result.get("attack_category", "unknown")
    attack_prompt   = result.get("attack_prompt", "")
    rationale       = result.get("rationale", "")
    attack_id       = result.get("attack_id", "")
    target_response = result.get("target_response")
    executed        = result.get("executed", False)
    icon            = CATEGORY_COLOURS.get(category, "⚪")
    exec_badge      = " ✅ Executed" if executed else ""

    label = f"{icon} **{category.replace('_', ' ').title()}**{exec_badge} — Prompt #{i}"

    with st.expander(label, expanded=(i == 1)):

        # ── Attack prompt ──────────────────────────────────────────────────────
        st.markdown("#### Attack Prompt")
        st.code(attack_prompt, language=None)

        # ── Rationale ─────────────────────────────────────────────────────────
        st.markdown("#### Rationale")
        st.info(rationale)

        # ── Target response ────────────────────────────────────────────────────
        st.markdown("#### Target Agent Response")
        if executed and target_response:
            st.code(target_response, language=None)
        elif executed and not target_response:
            st.warning("Attack was executed but no response was captured.")
        else:
            st.caption("Not executed — enable Execute mode in Configure Attacks to capture responses.")

        st.caption(f"attack_id: `{attack_id}`")

st.divider()

# ── Execute attacks ────────────────────────────────────────────────────────────
st.subheader("Execute Attacks")

unexecuted = [r for r in results if not r.get("executed")]
exec_count = len(unexecuted)

if exec_count == 0:
    st.success("All attacks have already been executed. Check the Execution Results page.")
else:
    st.caption(f"**{exec_count}** attack(s) pending execution.")

    use_sim = st.toggle(
        "Use LLM Simulation",
        value=True,
        help="LLM roleplays as the target agent. Turn off to POST to a real endpoint.",
        disabled=(exec_count == 0),
    )

    exec_url = None
    exec_ready = exec_count > 0
    if not use_sim:
        exec_url = st.text_input(
            "Target Agent URL *",
            placeholder="https://your-agent-endpoint.example.com/chat",
            help='Must accept POST with JSON body {"message": "..."}',
        )
        if not exec_url.strip():
            st.warning("Target URL is required when simulation is off.")
            exec_ready = False
        else:
            st.success(f"Will POST to: `{exec_url.strip()}`")

    if st.button(
        f"Execute {exec_count} Attack(s)",
        type="primary",
        disabled=not exec_ready,
        use_container_width=True,
    ):
        with st.status(f"Executing {exec_count} attack(s)...", expanded=True) as status:
            st.write(f"Mode: **{'LLM Simulation' if use_sim else exec_url}**")
            try:
                from services.agent_client import execute_attacks
                exec_output = execute_attacks(
                    existing_results=results,
                    agent_profile=agent,
                    use_simulation=use_sim,
                    target_url=exec_url.strip() if exec_url else None,
                )
                st.session_state["execution_results"] = exec_output
                st.session_state["execution_agent"]   = agent
                executed_now = exec_output.get("total_executed", 0)
                status.update(
                    label=f"Done — {executed_now} response(s) captured.",
                    state="complete",
                    expanded=False,
                )
            except Exception as e:
                status.update(label="Execution failed", state="error")
                st.error(f"Error: {e}")
                st.stop()

        st.switch_page("pages/3_Execution_Results.py")
