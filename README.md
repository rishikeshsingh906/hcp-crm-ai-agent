# AI-First CRM — HCP Module: Log Interaction Screen

A prototype "Log Interaction" screen for a pharmaceutical field rep CRM. Reps can
log a visit with a Healthcare Professional (HCP) via a **structured form** or by
just **chatting naturally** with an AI agent — both paths land in the same
database record, generated/enriched by an LLM through a LangGraph agent.

## Why it's built this way

Field reps lose time to admin work. The core idea here is that logging an
interaction shouldn't require translating a conversation into a form by hand —
the AI agent should do that translation, while still giving the rep a
structured, editable, compliance-checked record underneath.

## Stack

| Layer | Tech |
|---|---|
| Frontend | React 18 + Redux Toolkit, Vite, Google Inter |
| Backend | Python, FastAPI |
| Agent framework | LangGraph (ReAct-style tool-calling loop) |
| LLM | Groq — `gemma2-9b-it` (primary), `llama-3.3-70b-versatile` (fallback) |
| Database | Postgres or MySQL (SQLite works out of the box for local dev) |

## Project structure

```
hcp-crm/
├── backend/
│   ├── app/
│   │   ├── agent/
│   │   │   ├── llm.py        # Groq client wrapper + JSON extraction helper
│   │   │   ├── tools.py      # the 5 LangGraph tools
│   │   │   └── graph.py      # the LangGraph StateGraph (agent <-> tools loop)
│   │   ├── routers/
│   │   │   ├── hcp.py            # HCP CRUD
│   │   │   ├── interactions.py   # structured-form path (calls tools directly)
│   │   │   └── chat.py           # conversational path (runs the full agent)
│   │   ├── models.py         # SQLAlchemy models (HCP, Interaction, FollowUp)
│   │   ├── schemas.py        # Pydantic request/response schemas
│   │   ├── database.py
│   │   ├── config.py
│   │   ├── seed.py           # demo HCP data
│   │   └── main.py           # FastAPI app entrypoint
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── LogInteractionScreen.jsx  # the screen — toggles form/chat
    │   │   ├── StructuredForm.jsx
    │   │   ├── ChatInterface.jsx
    │   │   ├── HcpSelector.jsx
    │   │   └── InteractionHistory.jsx
    │   ├── store/            # Redux slices: hcp, interactions, chat
    │   ├── api/client.js      # axios instance
    │   └── index.css          # design tokens + all styling
    └── package.json
```

## The LangGraph agent

**Role.** The agent sits between freeform rep input (typed chat, or the raw
notes field on the structured form) and the CRM's relational data model. It
decides, turn by turn, whether to call a tool or ask a clarifying question,
and never lets a conversation end without either a saved record or an
explicit "not logged yet" state. It's a standard ReAct loop built with
`langgraph.prebuilt.ToolNode` / `tools_condition`:

```
START -> agent (LLM decides) -> tools (if requested) -> agent -> ... -> END
```

The structured-form submission path also runs through the same
`log_interaction` / `check_compliance` tools (see `routers/interactions.py`) —
so both entry points share one pipeline instead of duplicating logic.

### The 5 tools (`app/agent/tools.py`)

1. **`log_interaction`** *(required)* — Takes raw notes or a chat transcript
   and creates a new `Interaction` row. It calls the LLM
   (`extract_json` in `llm.py`) with a structured-extraction prompt to
   produce: a 2–3 sentence summary, a list of topics/products discussed, any
   samples distributed (`[{product, qty}]`), and the HCP's sentiment
   (positive/neutral/negative). This is what lets a rep type "Met Dr. Rao,
   went over the new cardiac trial, left 2 sample packs, she seemed
   interested" and get a fully structured record back.

2. **`edit_interaction`** *(required)* — Patches an existing `Interaction`.
   If the rep supplies new raw notes (e.g. "actually, change that to say we
   discussed dosing, not samples"), the tool re-runs the same LLM extraction
   pipeline against the new text. It also accepts direct field overrides
   (`summary`, `topics_discussed`, `sentiment`, `channel`) for cases where the
   rep wants to hand-correct the AI's output rather than re-describe the
   whole visit.

3. **`get_hcp_profile`** — Looks up an HCP's profile (specialty, institution,
   preferences) plus their `N` most recent interactions, so the agent has
   context before logging a new visit or answering a rep's question about
   that HCP's history.

4. **`schedule_followup`** — Creates a `FollowUp` row tied to an interaction
   (e.g. "send the Phase III data in two weeks"), so next-step commitments
   made mid-conversation aren't lost.

5. **`check_compliance`** — Runs the LLM over an interaction's notes with a
   compliance-focused prompt to flag potential issues: off-label promotion,
   kickback-adjacent language, or gifting beyond typical educational-item
   value. Sets `compliance_flag` / `compliance_notes` on the record. Run
   automatically after every `log_interaction` call.

## Running it locally

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # or your preferred env tool
pip install -r requirements.txt

cp .env.example .env
# edit .env and set GROQ_API_KEY (create one at https://console.groq.com/keys)
# DATABASE_URL defaults to sqlite:///./hcp_crm.db for zero-config local runs;
# swap in a postgresql+psycopg2://... or mysql+pymysql://... URL for real use.

python -m app.seed          # seeds 3 demo HCPs
uvicorn app.main:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs`.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` to `http://localhost:8000`
(see `vite.config.js`), so no CORS setup is needed in dev.

## Using either logging path

- **Structured form**: pick an HCP, fill in channel + notes, hit Save. The
  notes are sent through `log_interaction` server-side and you'll see the
  AI-generated summary appear immediately.
- **Conversational**: pick an HCP, switch to "Conversational", and just
  describe the visit in the chat box. Watch for the small tool-name tags
  above the agent's replies — they show which of the 5 tools fired on that
  turn.

## Notes / known simplifications

- Auth is intentionally out of scope for this prototype — `rep_name` is a
  free-text field rather than a logged-in user.
- The agent is stateless per HTTP request (LangGraph's checkpointing was left
  out); the Redux `chat` slice holds full conversation history client-side
  and resends it each turn.
- `gemma2-9b-it` is fast but occasionally inconsistent with strict JSON —
  `extract_json()` in `llm.py` includes a fallback brace-matching parser, and
  `chat_completion()` falls back to `llama-3.3-70b-versatile` if a call
  errors out.
