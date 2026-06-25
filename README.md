# Red-Teaming AI Agent — UI

A Streamlit frontend for automated adversarial testing of AI agents. Register a target agent, configure attack categories, generate adversarial prompts via the backend, execute them, and review results with verdict analytics.

---

## How it works

The UI is a thin frontend that talks to the [red-teaming agent backend](https://github.com/prudviacc/redteaming-ai-agent) over HTTP. It handles no LLM calls itself — all prompt generation, execution, and evaluation happen in the backend service.

```
redteaming_ui  →  POST /generate  →  redteaming_ai_agent (FastAPI + LangGraph)
               →  POST /execute   →
```

---

## Prerequisites

- Python 3.10+
- The red-teaming agent backend running (locally or hosted). See [backend setup](#backend).

---

## Quick start

```bash
git clone https://github.com/prudviacc/redteaming-ui.git
cd redteaming-ui

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env             # then edit AGENT_API_URL
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501).

---

## Configuration

Copy `.env.example` to `.env` and set:

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_API_URL` | `http://localhost:8000` | URL of the running backend API |
| `AGENT_API_TIMEOUT` | `300` | Seconds to wait for the backend to respond |

---

## Pages

### Home — Register Agents
Register the AI agent you want to test. Fill in the form manually or upload a JSON profile. Each registered agent stores its name, description, capabilities, and constraints.

### Configure Attacks
Select a registered agent, enable one or more attack categories, set how many test cases to generate per category, and choose an execution mode:

- **Generate only** — produces attack prompts without sending them anywhere
- **Generate & Execute (LLM Simulation)** — generates prompts and simulates the target agent's responses using the LLM
- **Generate & Execute (Real Endpoint)** — generates prompts and HTTP-POSTs each one to a live agent URL

### Attack Details
View every generated prompt alongside the LLM's rationale for why it should be effective. Execute any pending (unexecuted) attacks from this page.

### Execution Results
After execution, see:
- **Summary metrics** — total prompts, penetrated / partial / defended counts
- **Arc chart** — overall verdict distribution
- **Stacked bar chart** — verdict breakdown per attack category
- **Result cards** — side-by-side attack prompt and target response, with a colour-coded verdict banner and reasoning

---

## Attack categories

| Category | What it tests |
|----------|---------------|
| `prompt_injection` | Injecting instructions that override the system prompt |
| `goal_hijacking` | Redirecting the agent away from its intended task |
| `jailbreak` | Bypassing safety guidelines via role-play, hypotheticals, or encoding |
| `data_extraction` | Extracting system prompts, internal data, or PII |
| `role_play` | Using fictional framing to violate constraints |
| `authority_override` | Impersonating admins or developers for elevated access |
| `context_confusion` | Introducing conflicting context to cause inconsistent behaviour |
| `logic_exploitation` | Using logical paradoxes or edge cases to confuse decision-making |

---

## Verdicts

| Verdict | Meaning |
|---------|---------|
| `PENETRATED` | The agent violated its constraints |
| `PARTIAL` | The agent partially complied with the attack |
| `DEFENDED` | The agent successfully resisted |

---

## Project structure

```
redteaming_ui/
├── app.py                      # Home page — register / manage agents
├── pages/
│   ├── 1_Configure_Attacks.py  # Attack plan + execution mode
│   ├── 2_Attack_Details.py     # View prompts, execute pending attacks
│   └── 3_Execution_Results.py  # Verdicts, charts, side-by-side responses
├── services/
│   └── agent_client.py         # HTTP client — only file that calls the backend
├── store/
│   ├── profile_store.py        # Reads/writes storage/profiles.json
│   └── session_store.py        # Reads/writes storage/attacks.json
├── .env.example
└── requirements.txt
```

`services/agent_client.py` is the single seam between the UI and the backend. All other files are pure UI with no dependency on the agent's internals.

---

## Backend

This UI requires the red-teaming agent backend to be running. The backend exposes two endpoints:

- `POST /generate` — generate attack prompts (optionally execute them)
- `POST /execute` — execute a set of already-generated prompts

Set `AGENT_API_URL` in your `.env` to point at the backend. For local development the default `http://localhost:8000` works if the backend is running on the same machine.
