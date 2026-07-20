# Cairn — Frontend

The demo surface. A phone-framed chat on the left, a live tool trace on the
right.

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
```

---

## Running it

Backend first — see [../backend/README.md](../backend/README.md).

```bash
cd frontend
npm install
npm run dev          # :5173
```

Open <http://localhost:5173>.

`vite.config.js` proxies `/api` → `http://localhost:8000`. Change the target
there if uvicorn runs elsewhere. The backend also sets CORS for `:5173`, so
direct calls work too — the proxy just keeps the browser same-origin, which
matters if auth is ever added.

---

## How it works

### One endpoint drives everything

| Endpoint | Used for |
|---|---|
| `GET /api/me` | Right-pane identity, welcome message |
| `GET /api/health` | The online/offline status dot |
| `POST /api/chat` | **Everything else** |

There are deliberately **no** `/api/sessions` or `/api/attendees` endpoints.
`POST /api/chat` returns `tool_activity` — a trace of every tool the agent
called, *including each tool's full result*. That result payload is the card
data. Adding endpoints to re-fetch what the agent already returned would mean
the same data arriving by two paths, free to disagree.

### The data flow

```
POST /api/chat
      │
      └─> { answer, tool_activity: [ {tool, args, result}, ... ], offline? }
                    │
      ┌─────────────┴─────────────┐
      │                           │
  cardsFromActivity()        flatMap over all turns
  (lib/cards.js)             (TracePane)
      │                           │
   phone cards               the trace log
```

**Each assistant message carries its own `activity` array.** This is the key
structural decision. A single global activity array would break the
message↔card association on the second turn — you'd have no way to know which
tool calls produced which message's cards. Scoping activity to the message
solves both views from one source:

- The chat renders cards from `message.activity`
- The trace renders `messages.flatMap(m => m.activity)`

### Card derivation

`lib/cards.js` is the only place that decides what becomes a card. Not every
tool call does — `whoami` and `search_faq` are trace-only, because their results
are better expressed as the agent's prose than as a UI element.

| Tool | Card |
|---|---|
| `find_attendees` | Stacked attendee cards |
| `find_sessions` | Horizontal carousel |
| `my_registrations` | Schedule list (vertical — see below) |
| `register_for_session` | Outcome (success **or refusal**) |
| `cancel_registration` | Outcome |

The registrations card is a **list, not a carousel**, and that's deliberate:
sessions are a browse-and-choose, but your own schedule is a scan
top-to-bottom where the registration ID matters.

### File layout

```
src/
├── App.jsx                  owns conversation state; the only stateful component
├── lib/
│   ├── api.js               the only module that knows endpoints exist
│   ├── cards.js             tool_activity → cards
│   └── format.js            names, avatars, dates — presentation only
├── components/
│   ├── PhoneChat.jsx        the phone frame + chat
│   ├── TracePane.jsx        identity, status, trace log
│   ├── CairnStack.jsx       the signature element
│   ├── AttendeeCard.jsx
│   ├── SessionCarousel.jsx
│   ├── RegistrationsCard.jsx
│   └── OutcomeCard.jsx
└── styles/tokens.css        design tokens
```

Each component owns a sibling `.css` file. No CSS framework — the design is
specific enough that utility classes would be more code, not less.

---

## Design decisions

### Two visual languages, one accent

The panes are deliberately *not* unified. The phone is a consumer product:
warm paper (`#FBFAF8`), soft radii, Inter. The rail is machinery: cold basalt
(`#14181D`), hairline rules, JetBrains Mono. They share exactly one accent
(moss, `#4A6B52`).

**The contrast is the thesis.** Product on the left, the work behind it on the
right. A unified palette would have made it one app with a sidebar; the split
makes it a demo *about* what's under the app.

### Moss, not terracotta

Cairn is a trail marker. The accent is a muted trail-green, and the palette
avoids the looks AI-generated design defaults to (warm cream + terracotta serif;
near-black + acid green). `--clay` (`#B4593A`) exists and is reserved for **one**
thing: business-rule refusals. It appears nowhere else, so when you see it, a
rule fired.

### The signature: the cairn stack

Top-left of the trace pane. One stone per tool call in the current turn,
stacked bottom-up and tapering like a real cairn; it breathes while the agent is
working. A cairn marks a trail where the path isn't obvious — placed by people
who came before, for people coming after. Here it's literal and functional: you
can read at a glance how much work a question took.

Capped at five stones — past that it stops reading as stone and becomes a bar
chart.

### Cards were sized to the phone, not to the API

The 390px viewport is a hard constraint, and it drove real changes:

- **Session cards are 300×~184, not square.** A square is an awkward shape for
  text-heavy content and would either overflow or truncate hard. Description is
  clamped to two lines; the full text lives in the trace pane. **The phone shows
  the answer; the rail shows the evidence.**
- **300px inside 390px, with 14px padding, leaves ~48px of the next card
  peeking** — enough to read as "swipe", not so much it looks broken.
- **Attendee cards are compact** — avatar, name, one context line, three
  actions. Attendees are a *lookup*; sessions are a *browse*. The asymmetry is
  intentional.

### Avatars are initials, not photos

We have no headshots and won't generate faces for fictional people. Initials on
a deterministic colour (hue hashed from the attendee id) reads as designed
rather than as a missing image — it's what enterprise apps do for users without
photos, and it costs zero assets.

`parseName()` strips honorifics, so **Dr. Amara Okonkwo** renders `AO`, not
`DO`, and the welcome says "Welcome, Amara", not "Welcome, Dr."

### Register buttons make the backend visible

A session card's **Register** button sends a chat message rather than hitting a
REST endpoint. Two reasons: every mutation flows through the agent (one path,
one set of rules), and the entitlement refusal renders *in the conversation*
where it's most demonstrative.

The button sends the session_id to the agent but displays clean prose to the
user — `ses-004` is system vocabulary and has no business in a human's message
bubble.

### Copy

Errors are specific and actionable ("Check the backend is running on :8000"),
not vague and not apologetic. The empty registrations state is an invitation
("Ask about sessions to find something"), not a shrug. The backend already wrote
the refusal message, so we render it rather than inventing phrasing on top.

---

## Known gaps

- **No markdown rendering.** `.bubble` uses `white-space: pre-wrap` with no
  parser, so any `**bold**` from the model renders as literal asterisks. 
	Currently handled via the backend styling rules in system_prompt.
- **`OutcomeCard`'s waitlist branch is unreachable.** It renders an "Added to
  waitlist" state that the backend never produces — capacity was
  [deliberately scoped out](../backend/README.md#scoped-out-capacity-and-waitlisting),
  and the enum value is a placeholder for future work. The branch is kept in
  step with the backend vocabulary rather than removed.
- **No conversation persistence.** Refresh clears it. The premise is a single
  demo session; the backend store is in-memory anyway.
- **Below 1100px the panes stack.** The demo is a desktop story, but a broken
  layout in a narrow window is a bad look in any room.
