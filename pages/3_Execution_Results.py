"""Step 3 — Execution results: verdicts, responses, and attack analytics."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import altair as alt
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Execution Results", layout="wide")
st.title("Execution Results")
st.caption("Each attack prompt, the target agent's response, and whether the agent was penetrated or defended.")

output = st.session_state.get("execution_results")
agent  = st.session_state.get("execution_agent", {})

if not output:
    st.info("No execution results yet. Run attacks from the **Attack Details** page.")
    st.stop()

results        = output.get("results", [])
total          = output.get("total_generated", len(results))
total_executed = output.get("total_executed", 0)

executed_results = [r for r in results if r.get("executed")]
penetrated = sum(1 for r in executed_results if r.get("verdict") == "PENETRATED")
partial    = sum(1 for r in executed_results if r.get("verdict") == "PARTIAL")
defended   = sum(1 for r in executed_results if r.get("verdict") == "DEFENDED")

# ── Top metrics ────────────────────────────────────────────────────────────────
st.subheader("Summary")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Target Agent",   agent.get("name", "—"))
c2.metric("Total Prompts",  total)
c3.metric("Penetrated",     penetrated, delta=None, help="Agent violated its constraints")
c4.metric("Partial",        partial,    delta=None, help="Agent partially complied")
c5.metric("Defended",       defended,   delta=None, help="Agent successfully resisted")

st.divider()

# ── Charts ─────────────────────────────────────────────────────────────────────
st.subheader("Analytics")
chart_col1, chart_col2 = st.columns(2)

VERDICT_COLOURS = {
    "Penetrated": "#EF4444",
    "Partial":    "#F97316",
    "Defended":   "#22C55E",
}

# Arc chart — overall verdict distribution
with chart_col1:
    if total_executed > 0:
        donut_df = pd.DataFrame({
            "Verdict": ["Penetrated", "Partial", "Defended"],
            "Count":   [penetrated, partial, defended],
        })
        donut_df = donut_df[donut_df["Count"] > 0]
        donut_df["Percentage"] = (donut_df["Count"] / donut_df["Count"].sum() * 100).round(1)
        donut_df["Label"]      = donut_df["Verdict"] + " (" + donut_df["Percentage"].astype(str) + "%)"

        arc = (
            alt.Chart(donut_df, title="Overall Verdict Distribution")
            .mark_arc(innerRadius=60, outerRadius=110)
            .encode(
                theta=alt.Theta("Count:Q"),
                color=alt.Color(
                    "Verdict:N",
                    scale=alt.Scale(
                        domain=list(VERDICT_COLOURS.keys()),
                        range=list(VERDICT_COLOURS.values()),
                    ),
                    legend=alt.Legend(title=""),
                ),
                tooltip=["Verdict:N", "Count:Q", "Percentage:Q"],
            )
            .properties(height=280)
        )
        st.altair_chart(arc, use_container_width=True)
    else:
        st.info("No executed results to chart.")

# Stacked bar chart — verdict breakdown per category
with chart_col2:
    if executed_results:
        cat_rows = [
            {
                "Category": r["attack_category"].replace("_", " ").title(),
                "Verdict":  r.get("verdict", "DEFENDED").capitalize(),
            }
            for r in executed_results
        ]
        cat_df = (
            pd.DataFrame(cat_rows)
            .groupby(["Category", "Verdict"])
            .size()
            .reset_index(name="Count")
        )
        bar = (
            alt.Chart(cat_df, title="Verdict by Attack Category")
            .mark_bar()
            .encode(
                x=alt.X("Category:N", axis=alt.Axis(labelAngle=-30)),
                y=alt.Y("Count:Q", stack="zero"),
                color=alt.Color(
                    "Verdict:N",
                    scale=alt.Scale(
                        domain=list(VERDICT_COLOURS.keys()),
                        range=list(VERDICT_COLOURS.values()),
                    ),
                    legend=alt.Legend(title=""),
                ),
                tooltip=["Category:N", "Verdict:N", "Count:Q"],
            )
            .properties(height=280)
        )
        st.altair_chart(bar, use_container_width=True)
    else:
        st.info("No executed results to chart.")

st.divider()

# ── Filters ────────────────────────────────────────────────────────────────────
st.subheader("Attack Details")

categories_used = sorted({r["attack_category"] for r in results})
f1, f2, f3 = st.columns([3, 1, 1])

with f1:
    filter_options = ["All Categories"] + [c.replace("_", " ").title() for c in categories_used]
    filter_label   = st.selectbox("Category", filter_options)
with f2:
    verdict_filter = st.selectbox("Verdict", ["All", "Penetrated", "Partial", "Defended"])
with f3:
    exec_filter = st.selectbox("Status", ["All", "Executed", "Pending"])

filtered = results
if filter_label != "All Categories":
    raw_cat  = filter_label.lower().replace(" ", "_")
    filtered = [r for r in filtered if r["attack_category"] == raw_cat]
if verdict_filter != "All":
    filtered = [r for r in filtered if r.get("verdict", "").capitalize() == verdict_filter]
if exec_filter == "Executed":
    filtered = [r for r in filtered if r.get("executed")]
elif exec_filter == "Pending":
    filtered = [r for r in filtered if not r.get("executed")]

st.caption(f"Showing **{len(filtered)}** of **{total}** attack(s).")

# ── Result cards ───────────────────────────────────────────────────────────────
VERDICT_CONFIG = {
    "PENETRATED": {"icon": "🔓", "colour": "#EF4444", "label": "Penetrated"},
    "PARTIAL":    {"icon": "⚠️", "colour": "#F97316", "label": "Partial"},
    "DEFENDED":   {"icon": "🛡️", "colour": "#22C55E", "label": "Defended"},
}
CATEGORY_ICON = {
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
    target_response = result.get("target_response")
    executed        = result.get("executed", False)
    verdict         = result.get("verdict")
    verdict_reason  = result.get("verdict_reason", "")
    attack_id       = result.get("attack_id", "")

    cat_icon    = CATEGORY_ICON.get(category, "⚪")
    vcfg        = VERDICT_CONFIG.get(verdict, {"icon": "⏭", "colour": "#6B7280", "label": "Pending"})
    header_line = (
        f"{cat_icon} **{category.replace('_', ' ').title()}** "
        f"&nbsp;|&nbsp; {vcfg['icon']} **{vcfg['label']}** "
        f"&nbsp;|&nbsp; #{i}"
    )

    with st.container(border=True):
        st.markdown(header_line)

        if executed and verdict:
            # Coloured verdict banner
            st.markdown(
                f"<div style='background:{vcfg['colour']}22; border-left:4px solid {vcfg['colour']};"
                f"padding:8px 12px; border-radius:4px; margin-bottom:8px;'>"
                f"<b>{vcfg['icon']} {vcfg['label']}</b> — {verdict_reason}"
                f"</div>",
                unsafe_allow_html=True,
            )

        left, right = st.columns(2)

        with left:
            st.markdown("**Attack Prompt**")
            st.code(attack_prompt, language=None)
            with st.expander("Generation Rationale"):
                st.write(rationale)

        with right:
            st.markdown("**Target Agent Response**")
            if executed and target_response:
                st.code(target_response, language=None)
            elif executed and not target_response:
                st.warning("Executed but no response was captured.")
            else:
                st.caption("Not yet executed.")

        st.caption(f"attack_id: `{attack_id}`")

st.divider()

# ── Navigation ─────────────────────────────────────────────────────────────────
col_back, col_new = st.columns(2)
with col_back:
    if st.button("← Back to Attack Details", use_container_width=True):
        st.switch_page("pages/2_Attack_Details.py")
with col_new:
    if st.button("Configure New Attacks →", use_container_width=True):
        st.switch_page("pages/1_Configure_Attacks.py")
