# Cairn — Backend

FastAPI service behind the Meridian Summit concierge agent. Three hybrid
retrievers, seven tools the model routes between, a record store that enforces
business rules in Python, and an offline fallback so nothing hard-fails in a
demo.

---

## Running it

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m uvicorn main:app --reload
```

Serves on `:8000`. No credentials needed — it starts in offline mode.

> **Use the venv.** `python -m uvicorn` rather than bare `uvicorn` invokes it
> through the interpreter you just activated, so it can't resolve to a
> different Python via PATH. Activation doesn't persist across shells; a new
> terminal needs `source .venv/bin/activate` again.

### Running against Vertex

```bash
export USE_VERTEX=true
export GCP_PROJECT_ID=your-project
export GCP_REGION=us-central1                 # optional, defaults to us-central1
gcloud auth application-default login
python -m uvicorn main:app --reload
```

Model strings are overridable: `GEMINI_MODEL` (default `gemini-2.5-flash`) and
`EMBEDDING_MODEL` (default `text-embedding-005`).

### Environment

| Variable | Default | Effect |
|---|---|---|
| `USE_VERTEX` | unset | `true`/`1`/`yes` enables Vertex embeddings + Gemini |
| `GCP_PROJECT_ID` | — | Required when `USE_VERTEX` is on |
| `GCP_REGION` | `us-central1` | Vertex region |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Reasoning model |
| `EMBEDDING_MODEL` | `text-embedding-005` | Embedding model |
| `ACTIVE_ATTENDEE_ID` | unset | Pins the active attendee (e.g. `att-1008`) instead of picking randomly |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated allowed origins |

`ACTIVE_ATTENDEE_ID` matters more than it looks. Random selection is good for
showing variety and terrible for debugging — "it broke, but I can't reproduce
it, different attendee." One env var makes a run deterministic, and lets you
demo specific cases on purpose:

| Attendee | Why |
|---|---|
| `att-1008` | Trevor Nakamura, **Explorer** — every workshop registration gets refused on entitlement |
| `att-1002` | Rafael Ortiz, Builder — heavily registered, good for conflict detection |
| `att-1013` | Lena Warsaw, speaker — exercises the speaker path |

---

## Layout

```
cairn/
├── paths.py            DATA_DIR — defined once, imported everywhere
├── loaders.py          JSON → typed dataclasses (the parse boundary)
├── embeddings.py       Vertex embedder or offline fallback
├── registry.py         composition root; lru_cache singletons
│
├── retrieval/          "find things"
│   ├── searchable.py       the Searchable protocol
│   ├── models.py           Article · Attendee · Session
│   ├── hybrid_retriever.py generic BM25 + dense + RRF
│   └── attendee_retriever.py  subclass: exact-match + filters
│
├── records/            "change things"
│   ├── models.py           SessionRegistration, outcomes, errors
│   ├── store.py            the RecordStore protocol
│   └── memory_store.py     the implementation + business rules
│
└── agents/             "decide what to do"
    ├── system_prompt.py    grounding, routing, privacy, style
    ├── tools.py            7 tool impls + declarations
    ├── model.py            Gemini construction (cached)
    ├── agent.py            the tool loop
    └── offline.py          keyword routing fallback
```

Dependencies flow one direction: `main → agents → registry → loaders → paths`.
Nothing points back up. `retrieval/` and `records/` know nothing about the
agent, the web layer, or each other.

---

## Retrieval

### Hybrid, because neither half is enough

Every corpus is searched by **BM25 (lexical) and dense embeddings (semantic)**
in parallel, then fused with **Reciprocal Rank Fusion**.

The two catch different things. BM25 nails exact policy terms — "45 days",
"price adjustment", a company name. Dense retrieval catches paraphrase: a query
for "RAG safety" should surface a profile about "prompt injection defense" even
though they share no words.

RRF fuses the two ranked lists without tuning a weight:

```
score(doc) = Σ  1 / (k + rank_in_list)
```

That's the robust default when you can't calibrate score scales across
retrievers — BM25 scores and cosine similarities aren't on a comparable scale,
so blending the raw numbers is meaningless. Ranks are comparable; scores aren't.

### One engine, three configurations

`HybridRetriever[T]` is generic over anything satisfying `Searchable` — an
object with an `id` and a `searchable_text` property. It never imports `Article`
or `Session`; the models never import the retriever. They meet at the protocol.

That single decoupling is why three corpora share one engine:

```python
HybridRetriever(load_articles(),  embed)   # HybridRetriever[Article]
HybridRetriever(load_sessions(),  embed)   # HybridRetriever[Session]
AttendeeRetriever(load_attendees(), embed) # subclass — see below
```

Each model's `searchable_text` decides what's worth indexing. That's the *only*
place corpus-specific knowledge lives.

Results come back as `ScoredResult[T]` — the original item, untouched, with the
retrieval metadata alongside. Scores are facts about *this query*, not
properties of a Session, so they don't get bolted onto the domain object. `T`
flows through the wrapper, so `result.item.date` still type-checks as a `date`.

### AttendeeRetriever earns its subclass

Attendees are the one corpus that *behaves* differently, not just holds
different data:

1. **Exact identifier → keyed lookup.** A query that's a full email address
   short-circuits to a dict lookup and returns exactly one record. Hybrid search
   returns a *ranked list*; when the user names a specific person, they want
   *that* person, deterministically.
2. **Structured filters → filter, then rank.** `email_domain` and `company` are
   applied as hard constraints first; the semantic query is then ranked over the
   survivors. "Find someone in applied AI with a @google.com email" has a
   semantic part *and* a literal constraint — the constraint isn't a preference
   to blend, it's a filter to enforce.
3. **Otherwise → inherited hybrid**, unchanged.

The model never sees these three paths. It calls one `find_attendees` tool.
**Tools express intent; strategy selection is internal** — whether to use exact
or semantic matching is a deterministic string check, not a decision worth an
LLM round-trip.

Note what the tool schema *does* expose: named parameters `email_domain` and
`company`, not an `{operator, value}` filter grammar. The field name encodes the
match mode (exact vs. suffix), so the model just drops a value in the right slot
and Python derives `=` vs. `LIKE`. Asking the model for operators would mean
validating a query language it might get wrong.

---

## Records

### The store is bound to one attendee

`InMemoryStore(attendee, sessions)` takes the active attendee at construction.
Every method acts on their behalf. There is no `attendee_id` parameter anywhere.

This is **authorization by construction**, which is stronger than authorization
by check. The store *cannot* act for another user because it doesn't hold their
data. The model can't hallucinate an ID it isn't asked for, and there's no
"whose registrations?" ambiguity to get wrong.

`cancel_registration` still carries an explicit ownership check as
defense-in-depth, and returns `None` for both "not found" and "not yours" —
distinguishable errors would leak which registration IDs exist.

### Rules in Python, not in the prompt

The model decides *whether to register someone*. The store decides *whether
that's allowed*:

| Rule | Behavior |
|---|---|
| **Idempotency** | Already registered → returns the existing registration with `outcome=already_registered`. Not an error — nothing failed, the desired end state holds. |
| **Entitlement** | Pass tiers are ordinal (`Explorer < Builder < Summit Executive`), compared by index against a minimum per session type. Explorer + workshop → `EntitlementError` naming both the required and held tier. |
| **Conflict** | Brute-force interval overlap against existing registrations: `new_start < other_end and other_start < new_end` — one comparison that catches partial overlap *and* containment. Back-to-back sessions correctly don't conflict. |

None of this is restated in the system prompt. If it were, changing
`_MIN_TIER` would silently make the prompt lie. Code owns policy; the prompt
owns judgment. The tool returns the refusal *and its reason*, and the model
explains it.

### Errors as data

Tools catch `RegistrationError` and return `{"ok": false, "message": ...}`
rather than letting it propagate. The model needs to *read* why something failed
to offer an alternative — an exception escaping to the framework gives it
nothing to work with.

The error hierarchy makes this one clause:

```
RegistrationError          ← base; also raised directly for unknown session
├── EntitlementError       ← pass tier insufficient
└── ConflictError          ← overlaps an existing registration
```

`except RegistrationError` catches all three.

### Outcomes are typed, not stringly

`session_register` returns a `RegistrationResult` — the registration *plus* a
`RegistrationOutcome` enum. Two different successes ("I registered you" vs.
"you already were") would otherwise be indistinguishable, and the agent would
confidently say the wrong one. The store reports what happened; the tool layer
decides how to phrase it.

---

## Agents

### Retrieval is a tool, not a pre-step

The naive design retrieves KB context on every turn and injects it into the
prompt. That's wrong for a multi-corpus agent: "who should I talk to about
vector infrastructure?" isn't answered by the FAQ, so you'd burn a retrieval,
inject four irrelevant chunks, and hope the model routes correctly *despite*
the context.

Instead, all three retrievers are tools. The model routes:

| Tool | For |
|---|---|
| `whoami` | Identity of the attendee being assisted |
| `search_faq` | The event itself — venue, passes, schedule, policy |
| `find_sessions` | Talks and workshops by topic |
| `find_attendees` | People by expertise, company, or email |
| `my_registrations` | The attendee's own schedule |
| `register_for_session` | Register (rules enforced in the store) |
| `cancel_registration` | Cancel |

Cost: one extra round-trip, since the model must *decide* to search before
searching. Worth it — the right corpus gets searched, the context stays clean,
and the tool called tells the UI which card to render.

**Tool descriptions are the routing logic.** They say what each tool is for
*and* what it isn't. When the model mis-routes, the fix is almost always a
sharper description, not more code.

### The tool loop

```
send message ──► model
      ▲            │
      │            ├── no function calls? ──► final answer, done
      │            │
      └── results ─┴── function calls ──► execute ──► feed back
                            (max 8 rounds)
```

The cap (`_LOOP_CAP`, 8 rounds) has a `for...else`: if the loop exhausts while
the model is still calling tools, `resp` is a function-call response and text
extraction would return an empty string — a blank reply. The `else` catches
exactly that case and returns an honest message instead.

`vertexai` is imported *inside* `_gemini_answer`, not at module top. A top-level
import would raise `ImportError` without the SDK installed, and the offline path
would die before `run_turn` ever checked `if model is None`.

### Offline fallback

`agents/offline.py` fakes the one thing Gemini does that's cheaply
approximable: choosing a tool. Regex intent patterns route to the **same
retrievers and the same store**; only routing and phrasing are hand-rolled.

Deliberately **read-only** — it routes to the three retrievers, `whoami`, and
`my_registrations`, never to register/cancel. A mis-routed read is a wrong
answer; a mis-routed write corrupts the demo.

Three patterns needed real work, and the reasons are instructive:

- `\b(my)\b.*\b(schedul` **fails on "my schedule"** — both word boundaries sit
  on the same space and `.*` can't match zero-width there. Uses `[\s\w']*`.
- A bare `my pass` in the identity pattern **stole "Can I upgrade my pass?"**
  from the FAQ. Removed.
- The proper-name pattern is **case-sensitive on purpose**. Under `re.I`,
  `[A-Z][a-z]+` matches any word, so "anything about hybrid retrieval" routed to
  people search.

It answers one question with one tool. It cannot chain, resolve pronouns, or
synthesize. That is the deal, and the docstring says so.

---

## Composition

`registry.py` is the composition root. Every expensive singleton is built once
behind `@lru_cache(maxsize=1)`:

```python
get_active_attendee()   # random pick — cached, so it behaves like a login
get_faq_retriever()     # indexes the corpus at first call
get_session_retriever()
get_attendee_retriever()
get_store()
```

`lru_cache` is doing real work on `get_active_attendee`: without it,
`random.choice` would run per call and you'd "log in" as a different person
mid-conversation.

The pattern is **lazy, then warmed**. Importing `registry` costs nothing;
`main.py`'s lifespan hook calls each getter at startup so the first user request
doesn't pay the embedding cost. Tests that don't touch retrieval never build it.

`get_model()` lives in `agents/model.py`, not the registry — it depends on the
prompt and tools, and putting it in `registry.py` would create a cycle
(`registry → agents → registry`).

---

## API

| Endpoint | Returns |
|---|---|
| `GET /api/health` | `{status, vertex_enabled}` |
| `GET /api/me` | The active attendee — id, name, title, company, pass_tier, interests |
| `POST /api/chat` | `{answer, tool_activity[], offline?}` |

`tool_activity` is the whole contract for the frontend. Each entry is
`{tool, args, result}` with the tool's **full result payload** — which is why
there are no `/api/sessions` or `/api/attendees` endpoints. The agent already
returned the data; re-fetching it would mean two paths to the same information,
free to disagree.

---

## Scoped out: capacity and waitlisting

Capacity limits were considered and **deliberately declined**, because enforcing
them would compromise the store's isolation guarantee to enforce a rule that
never fires.

The store is bound to one attendee at construction — that's what makes it
unable to act for anyone else. Entitlement and conflict both operate purely on
the active attendee's own data, which is why they fit the model cleanly and why
they were the right two rules to build.

Capacity doesn't fit the model cleanly. A headcount needs every attendee's
registrations, which means seeding all 18 into a store whose entire safety
property is that it only holds one person's rows. You'd trade a structural
guarantee — *cannot* act for another user — for a defensive check that a later
refactor could quietly drop. That's a bad trade for a limit that, at hundreds
of seats and a single registering user, would never bind.

Implementing it would need, in order: a `capacity` field added to all 11
sessions in `sessions.json` (it isn't in the data at all), the field threaded
through `Session` and `loaders.load_sessions`, all attendees' registrations
seeded for the headcount, and `cancel_registration`'s ownership check promoted
from defense-in-depth to load-bearing.

**`RegistrationStatus.WAITLIST` and `RegistrationOutcome.WAITLISTED` remain in
the enums as placeholders** for that future work. Nothing produces them today —
the `_render` and `OutcomeCard` branches that handle waitlist states are
unreachable. They're kept so the vocabulary exists if capacity is ever added,
rather than being retrofitted through three layers at that point.

## Known gaps

Stated plainly rather than hidden in a roadmap. Unlike capacity above, these
are things that should exist and don't.

**Seed registrations bypass every rule.** `InMemoryStore.__init__` writes
directly from `attendee.registered_sessions` with no entitlement, conflict, or
capacity check. Today's data doesn't violate anything, but nothing structurally
prevents a seeded Explorer holding a workshop. Either validate seeds through the
same path or document them as trusted fixtures — currently neither.

**No evaluation harness.** The offline router has a routing test; retrieval has
nothing. "How do you know retrieval is good?" currently has no answer. A gold
set of ~10 query→expected-article pairs and a recall@k script is ~30 minutes and
turns "I built RAG" into "I measured it."

**Single tenant by design.** `get_active_attendee()` is a process-wide
singleton — one user per server process. Multi-tenant means the attendee moves
from an `lru_cache` to a per-request dependency and the store becomes
per-session. The seam is known; it just isn't built.
