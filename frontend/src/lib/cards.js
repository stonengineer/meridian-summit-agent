/**
 * Deriving chat cards from tool activity.
 *
 * The backend returns ONE array per turn: `tool_activity`, a chronological
 * trace of every tool the agent called. Both panes read from it, but they want
 * different things:
 *
 *   · The rail wants the whole trace — every call, including boring ones like
 *     whoami, with args and raw results. It's evidence.
 *   · The phone wants only the calls whose results are *renderable*, attached
 *     to the message they belong to.
 *
 * So: the trace stays the source of truth, and this module derives cards from
 * it per-message. We do NOT add endpoints to re-fetch data the agent already
 * returned — that would mean the same data arriving by two paths, free to
 * disagree.
 */

/** Tools whose results become cards in the chat. Everything else is trace-only. */
const RENDERABLE = new Set([
  "find_attendees",
  "find_sessions",
  "my_registrations",
  "register_for_session",
  "cancel_registration",
]);

/**
 * @param {Array} activity  tool_activity for a single assistant turn
 * @returns {Array} cards, in call order
 */
export function cardsFromActivity(activity = []) {
  const cards = [];

  for (const call of activity) {
    if (!RENDERABLE.has(call.tool)) continue;
    const result = call.result ?? {};

    switch (call.tool) {
      case "find_attendees": {
        const people = result.results ?? [];
        if (people.length) cards.push({ kind: "attendees", people });
        break;
      }
      case "find_sessions": {
        const sessions = result.results ?? [];
        if (sessions.length) cards.push({ kind: "sessions", sessions });
        break;
      }
      case "my_registrations": {
        const registrations = result.registrations ?? [];
        cards.push({ kind: "registrations", registrations });
        break;
      }
      case "register_for_session":
      case "cancel_registration": {
        // Write outcomes are always worth showing — especially failures, which
        // is where the entitlement and conflict rules become visible.
        cards.push({ kind: "outcome", tool: call.tool, result });
        break;
      }
      default:
        break;
    }
  }

  return cards;
}

/**
 * Session ids the user is currently registered for, read from this turn's
 * activity. Lets a session card render "Registered" instead of a dead button.
 * Only reflects what the agent looked up this turn — it is a hint, not state.
 */
export function registeredSessionIds(activity = []) {
  const ids = new Set();
  for (const call of activity) {
    if (call.tool === "my_registrations") {
      for (const r of call.result?.registrations ?? []) ids.add(r.session_id);
    }
    if (call.tool === "register_for_session" && call.result?.ok) {
      const id = call.args?.session_id;
      if (id) ids.add(id);
    }
  }
  return ids;
}
