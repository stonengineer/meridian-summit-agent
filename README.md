# Cairn

A grounded conference concierge agent, built as a working reference
implementation of the pattern behind production enterprise AI:
**unstructured knowledge → grounded answer → structured action.**

Cairn is the in-app assistant for *Meridian Summit 2026*, a fictional five-day
enterprise-AI conference at Moscone Center. Attendees ask it about sessions,
find people worth meeting, and register for talks. It answers only from the
event's own data, and it enforces business rules — pass-tier entitlements,
schedule conflicts — in deterministic code rather than trusting the model to
remember them.

Everything is synthetic. No real company, person, or event is represented.

```
┌──────────────────────────────┬─────────────────────────┐
│                              │  ▲ CAIRN     ● gemini   │
│      ┌──────────────┐        │  ─────────────────────  │
│      │  chat + cards│        │  ACTING AS              │
│      │              │        │  [TN] Trevor Nakamura   │
│      │  ┌─────────┐ │        │       Explorer          │
│      │  │ session │→│        │  ─────────────────────  │
│      │  │carousel │ │        │  TRACE                  │
│      │  └─────────┘ │        │  ▸ find_sessions        │
│      │ [Ask Cairn ] │        │  ▸ register_for_session │
│      └──────────────┘        │    ✕ EntitlementError   │
└──────────────────────────────┴─────────────────────────┘
   the product                       the machinery
```

---

## Why it looks like this

The demo is two panes because the interesting part of an AI system is invisible
by default. On the left, a phone-framed chat — the product an attendee would
actually use. On the right, a live trace of every tool the agent called, what it
searched, what came back, and why an action was refused.

If a reviewer wants to know whether the agent is grounded or improvising, the
right pane answers it without reading a line of code.

---

## Quick start

Two terminals. Backend first.

```bash
# Terminal 1
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m uvicorn main:app --reload        # :8000
```

```bash
# Terminal 2
cd frontend
npm install
npm run dev                                 # :5173
```

Open <http://localhost:5173>.

It runs immediately with **no cloud credentials** — see
[Offline mode](#offline-mode) below.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ frontend/  React + Vite                                     │
│   PhoneChat ── cards ──┐                                    │
│   TracePane ── trace ──┤ both read one payload              │
└────────────────────────┼────────────────────────────────────┘
                         │  POST /api/chat
┌────────────────────────┼────────────────────────────────────┐
│ backend/  FastAPI      ▼                                    │
│                                                             │
│   agents/     run_turn ──► Gemini + tool declarations       │
│                  │            │                             │
│                  │            └─► routes to one of 7 tools  │
│                  │                                          │
│                  ├─► retrieval/   hybrid search (BM25 +     │
│                  │                dense, fused with RRF)    │
│                  │      over FAQ · sessions · attendees     │
│                  │                                          │
│                  └─► records/     in-memory store; entitle- │
│                                   ment + conflict rules     │
│                                                             │
│   data/       four JSON files — the only source of truth    │
└─────────────────────────────────────────────────────────────┘
```

**The backend** does the work: three hybrid retrievers over separate corpora,
seven tools the model routes between, and a record store that enforces business
rules in Python. Retrieval is not a pre-step — it's a set of tools the model
chooses among, so a question about people searches people, not the FAQ.

**The frontend** is a rendering of one payload. `POST /api/chat` returns the
agent's answer plus `tool_activity` — a trace of every tool call *including its
full result*. That result payload is the card data, so there are deliberately no
`/api/sessions` or `/api/attendees` endpoints to re-fetch what the agent already
returned.

Details, decisions, and known gaps:

- **[backend/README.md](backend/README.md)** — retrieval, tools, the store, the
  agent loop, and what's next
- **[frontend/README.md](frontend/README.md)** — the two panes, card derivation,
  design system

---

## What it demonstrates

| | |
|---|---|
| **Hybrid retrieval** | BM25 lexical + dense semantic, fused with Reciprocal Rank Fusion — over three separate corpora |
| **Tool-routed RAG** | Retrieval is a set of tools the model picks between, not a fixed pre-step |
| **Structured extraction** | The model fills typed filter parameters (`email_domain`, `company`); Python decides how to match them |
| **Rules as code** | Pass-tier entitlement and schedule conflicts live in deterministic Python — the model can't be talked out of them |
| **Authorization by construction** | The store is bound to one attendee at init; it *cannot* act for anyone else |
| **Graceful degradation** | Runs with zero cloud credentials via a keyword-routed offline fallback |
| **Observability** | Every tool call, argument, and refusal is visible in the UI |

---

## Offline mode

Cairn runs with no GCP credentials. `USE_VERTEX` is unset by default, and both
model-dependent layers fall back:

| Layer | Online (`USE_VERTEX=true`) | Offline (default) |
|---|---|---|
| Embeddings | Vertex `text-embedding-005` | Hash-bucket histogram — keyword overlap, not semantics |
| Reasoning | Gemini + function calling | Regex intent routing → real tools → templated prose |

The offline path calls the **same retrievers and the same store** — only the
routing and phrasing are hand-rolled, and it is deliberately read-only. It is
demo insurance, not a second brain: it cannot chain tools, resolve pronouns, or
synthesize. Retrieval quality is also degraded, because hash embeddings match
words rather than meaning.

**Full behavior requires `USE_VERTEX=true`.** See
[backend/README.md](backend/README.md#running-against-vertex).

---

## The event

**Meridian Summit 2026** — "Where enterprise AI meets the people who ship it."
Five days at Moscone Center, September 14–18, 2026. Three pass tiers (Explorer,
Builder, Summit Executive) that actually gate what you can register for, 15 FAQ
articles, 11 sessions, and 18 attendees — 8 of whom are also speakers.

The data is small on purpose. It's large enough for retrieval to be non-trivial
and small enough that every referential edge is verifiable by hand.

---

## Repository

```
meridian-summit-agent/
├── backend/          FastAPI · retrieval · records · agent
│   ├── cairn/
│   ├── data/         the four JSON corpora
│   └── README.md     ← backend detail
├── frontend/         React · Vite
│   ├── src/
│   └── README.md     ← frontend detail
└── README.md         you are here
```

---

## Status

Working end to end in offline mode. Vertex integration is wired but not yet
exercised against a live project — that's the next session's work.

Known gaps are listed honestly in each sub-README rather than in a roadmap
here, because they're specific to their layer.
