import { useEffect, useMemo, useState } from "react";
import PhoneChat from "./components/PhoneChat.jsx";
import TracePane from "./components/TracePane.jsx";
import { fetchHealth, fetchMe, sendChat } from "./lib/api.js";
import { registeredSessionIds } from "./lib/cards.js";
import "./App.css";

/**
 * App root — owns all conversation state.
 *
 * The key structural decision: each assistant message carries its own
 * `activity` array. That's what lets the chat render cards next to the message
 * they belong to *and* lets the trace pane show a flat chronological log — one
 * source of truth, two views. Keeping a separate global activity array would
 * break the message↔card association after the second turn.
 */
export default function App() {
  const [me, setMe] = useState(null);
  const [health, setHealth] = useState(null);
  const [messages, setMessages] = useState([]);
  const [thinking, setThinking] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchMe().then(setMe).catch(() => setMe(null));
    fetchHealth()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  /**
   * Sessions we know are registered, accumulated across every turn's activity.
   * A hint for rendering "Registered" instead of a live button — the backend
   * remains the authority, and a stale hint costs nothing because
   * register_for_session is idempotent.
   */
  const registeredIds = useMemo(() => {
    const all = new Set();
    for (const m of messages) {
      for (const id of registeredSessionIds(m.activity)) all.add(id);
    }
    return all;
  }, [messages]);

  /**
   * @param {string} text     what the agent receives
   * @param {string} [display] what the user sees, when they differ
   *
   * They differ for card actions: tapping Register must send the session_id so
   * the agent doesn't have to re-search for it, but "ses-004" is system
   * vocabulary and has no business in a human's message bubble.
   */
  async function send(text, display) {
    setError(null);

    // The API wants prior turns only — role/content, no local card state.
    // History carries the agent-facing text so ids stay resolvable across turns.
    const history = messages.map((m) => ({
      role: m.role,
      content: m.sent ?? m.content,
    }));

    setMessages((m) => [
      ...m,
      { role: "user", content: display ?? text, sent: text },
    ]);
    setThinking(true);

    try {
      const data = await sendChat(text, history);
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: data.answer ?? "",
          activity: data.tool_activity ?? [],
          offline: data.offline === true,
        },
      ]);
      // A turn can flip the model's availability (creds expire mid-demo), so
      // re-read health rather than trusting the value from page load.
      fetchHealth().then(setHealth).catch(() => {});
    } catch (e) {
      setError(
        `Couldn't reach Cairn (${e.message}). Check the backend is running on :8000.`
      );
    } finally {
      setThinking(false);
    }
  }

  return (
    <div className="app">
      <PhoneChat
        me={me}
        messages={messages}
        thinking={thinking}
        error={error}
        registeredIds={registeredIds}
        onSend={send}
      />
      <TracePane me={me} health={health} messages={messages} thinking={thinking} />
    </div>
  );
}
