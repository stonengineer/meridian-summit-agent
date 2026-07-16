import { useEffect, useRef } from "react";
import CairnStack from "./CairnStack.jsx";
import { avatarStyle, parseName } from "../lib/format.js";
import "./TracePane.css";

/**
 * The right pane: who we're acting as, whether the model is live, and every
 * tool the agent has called.
 *
 * This is the glass box. The phone shows the product; this shows the work. It
 * reads the same `tool_activity` the cards do — one source, two views — but
 * shows *everything*, including calls that produce no card (whoami), plus args
 * and result summaries. If a demo reviewer wants to know whether the agent is
 * grounded or improvising, this is where they look.
 */
export default function TracePane({ me, health, messages, thinking }) {
  const logRef = useRef(null);

  // Flatten every turn's activity into one chronological trace.
  const trace = messages.flatMap((m) =>
    (m.activity ?? []).map((call) => ({ ...call, offline: m.offline }))
  );

  const lastTurnCalls = messages.length
    ? (messages[messages.length - 1].activity ?? []).length
    : 0;

  useEffect(() => {
    logRef.current?.scrollTo({
      top: logRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [trace.length, thinking]);

  const online = health?.vertex_enabled === true;
  const reachable = health != null;

  return (
    <aside className="trace">
      <header className="trace-brand">
        <CairnStack count={lastTurnCalls} thinking={thinking} />
        <div className="trace-brand-id">
          <div className="trace-name">Cairn</div>
          <div className="trace-sub">Meridian Summit · in-app assistant</div>
        </div>
        <StatusDot online={online} reachable={reachable} />
      </header>

      <section className="trace-block">
        <h2 className="trace-label">Acting as</h2>
        {me ? (
          <div className="trace-me">
            <div className="trace-avatar" style={avatarStyle(me.id)} aria-hidden="true">
              {parseName(me.name).initials}
            </div>
            <div className="trace-me-id">
              <div className="trace-me-name">{me.name}</div>
              <div className="trace-me-role">
                {me.title} · {me.company}
              </div>
              <div className="trace-chips">
                <span className="chip chip-tier">{me.pass_tier}</span>
                {me.interests?.slice(0, 3).map((i) => (
                  <span className="chip" key={i}>
                    {i}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="trace-dim">Loading identity…</div>
        )}
      </section>

      <section className="trace-block trace-log-block">
        <h2 className="trace-label">
          Trace
          {trace.length > 0 && <span className="trace-count">{trace.length}</span>}
        </h2>

        <div className="trace-log" ref={logRef}>
          {trace.length === 0 && !thinking && (
            <p className="trace-dim">
              Every tool the agent calls shows up here — what it searched, what
              came back, and why an action was refused.
            </p>
          )}

          {trace.map((call, i) => (
            <TraceEntry key={i} call={call} />
          ))}

          {thinking && (
            <div className="trace-working">
              <span />
              <span />
              <span />
            </div>
          )}
        </div>
      </section>
    </aside>
  );
}

function StatusDot({ online, reachable }) {
  const label = !reachable
    ? "Backend unreachable"
    : online
      ? "Gemini live"
      : "Offline routing";
  return (
    <div className={`status ${!reachable ? "is-down" : online ? "is-live" : "is-offline"}`}>
      <span className="status-dot" />
      <span className="status-text">{label}</span>
    </div>
  );
}

/** One tool call: what was asked, what came back. */
function TraceEntry({ call }) {
  const summary = summarize(call);
  const refused = call.result?.ok === false;

  return (
    <div className={`entry ${refused ? "is-refused" : ""}`}>
      <div className="entry-head">
        <span className="entry-tool">{call.tool}</span>
        {call.offline && <span className="entry-tag">offline</span>}
      </div>

      {Object.entries(call.args ?? {}).map(([k, v]) =>
        v == null || v === "" ? null : (
          <div className="entry-arg" key={k}>
            <span className="entry-key">{k}</span>
            <span className="entry-val">{String(v)}</span>
          </div>
        )
      )}

      <div className={`entry-out ${refused ? "is-refused" : ""}`}>
        {refused ? "✕ " : "→ "}
        {summary}
      </div>
    </div>
  );
}

/**
 * One line describing what a call returned. Deliberately terse — the trace is
 * scanned, not read. Anything longer belongs in the card.
 */
function summarize(call) {
  const r = call.result ?? {};

  if (r.ok === false) return r.message ?? "refused";

  switch (call.tool) {
    case "whoami":
      return `${r.name ?? "?"} · ${r.pass_tier ?? "?"}`;
    case "search_faq":
    case "find_sessions":
    case "find_attendees": {
      const n = (r.results ?? []).length;
      const top = r.results?.[0];
      const name = top?.title ?? top?.name ?? top?.question;
      return n === 0 ? "no matches" : `${n} result${n === 1 ? "" : "s"} · ${name}`;
    }
    case "my_registrations": {
      const n = (r.registrations ?? []).length;
      return `${n} registration${n === 1 ? "" : "s"}`;
    }
    case "register_for_session":
      return `${r.outcome ?? r.status ?? "ok"} · ${r.registration_id ?? ""}`.trim();
    case "cancel_registration":
      return `${r.status ?? "cancelled"} · ${r.registration_id ?? ""}`.trim();
    default:
      return "ok";
  }
}
