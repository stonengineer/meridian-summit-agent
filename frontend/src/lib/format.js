/**
 * Presentation helpers.
 *
 * Everything here turns backend data into something displayable. None of it
 * makes decisions the backend already made — it only formats.
 */

const HONORIFICS = new Set(["dr.", "dr", "prof.", "prof", "mr.", "mrs.", "ms."]);

/**
 * Split a display name into parts a UI can use.
 *
 * The backend's /api/me does NOT send first_name/last_name (attendees.json has
 * them, but me_payload() doesn't include them), so we derive here. The naive
 * `name.split(" ")[0]` renders "Welcome, Dr." for "Dr. Amara Okonkwo" — this
 * strips honorifics. If me_payload ever gains first_name, prefer that field
 * and delete this.
 */
export function parseName(fullName = "") {
  const parts = fullName.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return { first: "", last: "", initials: "?" };

  if (HONORIFICS.has(parts[0].toLowerCase()) && parts.length > 1) {
    parts.shift();
  }
  const first = parts[0] ?? "";
  const last = parts.length > 1 ? parts[parts.length - 1] : "";
  const initials = ((first[0] ?? "") + (last[0] ?? "")).toUpperCase() || "?";
  return { first, last, initials };
}

/**
 * Deterministic avatar hue from a stable id.
 *
 * We have no headshots and won't invent faces for fictional people. Initials on
 * a generated colour reads as designed rather than as a missing image, and it's
 * what enterprise apps do for users without photos. Hue is derived from the id
 * so a given person is always the same colour across renders.
 */
export function avatarStyle(id = "") {
  let hash = 0;
  for (let i = 0; i < id.length; i++) {
    hash = (hash * 31 + id.charCodeAt(i)) >>> 0;
  }
  const hue = hash % 360;
  return {
    background: `hsl(${hue} 24% 42%)`,
    color: `hsl(${hue} 30% 92%)`,
  };
}

/** "2026-09-15" -> "Tue Sep 15". Parsed as local, not UTC, to avoid a day shift. */
export function formatDate(iso = "") {
  const [y, m, d] = iso.split("-").map(Number);
  if (!y || !m || !d) return iso;
  const date = new Date(y, m - 1, d);
  return date.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

/** "11:00" -> "11:00 AM" */
export function formatTime(hhmm = "") {
  const [h, m] = hhmm.split(":").map(Number);
  if (Number.isNaN(h)) return hhmm;
  const suffix = h >= 12 ? "PM" : "AM";
  const hour = h % 12 === 0 ? 12 : h % 12;
  return `${hour}:${String(m).padStart(2, "0")} ${suffix}`;
}

/** Wall-clock time for the phone's mock status bar. */
export function clockNow() {
  return new Date().toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
  });
}
