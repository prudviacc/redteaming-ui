# Red-Teaming AI Agent — UI

Streamlit frontend for automated adversarial testing of AI agents. Register a target agent, configure attack categories, generate adversarial prompts via the backend, execute them, and review results with verdict analytics.

---

## How it works

The UI is a thin frontend that calls the red-teaming agent backend over HTTP. All prompt generation, execution, and evaluation happen in the backend.

```
redteaming_ui  →  POST /generate  →  redteaming_ai_agent (FastAPI + LangGraph)
               →  POST /execute   →
```

---

## Local development

**Prerequisites:** Python 3.11+, `az login`

```bash
cd redteaming_ui
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # set AGENT_API_URL
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501).

Set `AGENT_API_URL` in `.env` to point at the backend:

```
AGENT_API_URL=http://localhost:8000
AGENT_API_TIMEOUT=300
```

---

## Deployment

The UI is designed to run on Azure Container Apps alongside the backend service. A `Dockerfile` is included. See [DEPLOYMENT.md](DEPLOYMENT.md) for the full deployment guide.

---

## Pages

### Home — Register Agents
Register the AI agent you want to test. Fill in the form manually or upload a JSON profile. Agents can be edited, deleted, or exported as JSON.

### Configure Attacks
Select a registered agent, then either:

- **Quick Scan** — one click, all 8 categories × 2 prompts, LLM simulation
- **Advanced** — custom categories, test case counts, and execution mode

Execution modes (Advanced):

| Mode | What happens |
|------|-------------|
| Generate only | Produces attack prompts, no execution |
| Simulation | LLM roleplays as the target agent |
| Generic HTTP | HTTP POSTs each prompt to a live endpoint (custom headers + auth supported) |
| Azure AI Foundry | Connects to an Azure-deployed agent (project endpoint + agent ID + auth mode) |

### Attack Details
View every generated prompt alongside the rationale. Filter by category and execution status. Execute any pending (unexecuted) attacks from this page.

### Execution Results
After execution:
- **Security posture banner** — High / Medium / Low Risk with penetration rate %
- **Summary metrics** — total prompts, penetrated / partial / defended counts
- **Verdict distribution arc chart** — overall breakdown
- **Verdict by category stacked bar** — per-category breakdown
- **Result cards** — side-by-side attack prompt and target response with colour-coded verdict banner
- **Load previous session** — reload any past execution from history
- **Export** — download results as CSV or JSON

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
├── app.py                      # Home — register / manage agents
├── utils.py                    # render_sidebar() — backend ping + workflow steps
├── pages/
│   ├── 1_Configure_Attacks.py  # Quick Scan + Advanced attack config
│   ├── 2_Attack_Details.py     # View prompts, execute pending attacks
│   └── 3_Execution_Results.py  # Security posture, charts, result cards, export
├── services/
│   └── agent_client.py         # HTTP client — only file that calls the backend
├── store/
│   ├── profile_store.py        # Reads/writes storage/profiles.json
│   └── session_store.py        # Reads/writes storage/attacks.json
├── Dockerfile
├── .env.example
└── requirements.txt
```

`services/agent_client.py` is the single seam between the UI and backend. All other files are pure UI.
