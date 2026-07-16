/**
 * The only module that knows the backend exists.
 *
 * Components call these functions; they never fetch directly. That keeps the
 * API contract in one place and makes the "what shape does /api/chat return"
 * question answerable by reading one file.
 *
 * Contract (from backend/main.py):
 *   GET  /api/health  -> { status, vertex_enabled }
 *   GET  /api/me      -> { id, name, title, company, pass_tier, interests }
 *   POST /api/chat    -> { answer, tool_activity: [...], offline?: true }
 */

async function request(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    // Surface the status — a 500 from the agent and a 404 from a typo'd path
    // are very different problems, and "failed to fetch" hides both.
    throw new Error(`${options.method ?? "GET"} ${path} → ${res.status}`);
  }
  return res.json();
}

export function fetchHealth() {
  return request("/api/health");
}

export function fetchMe() {
  return request("/api/me");
}

/**
 * @param {string} message
 * @param {{role: string, content: string}[]} history  prior turns, oldest first
 */
export function sendChat(message, history) {
  return request("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message, history }),
  });
}
