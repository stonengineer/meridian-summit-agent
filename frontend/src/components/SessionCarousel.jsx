import { formatDate, formatTime } from "../lib/format.js";
import "./SessionCarousel.css";

/**
 * Horizontally scrolling session cards.
 *
 * Sessions are a *browse-and-choose*, so they get more room than attendees and
 * a swipe affordance. Cards are 300px wide inside a 390px phone: with 14px page
 * padding each side, ~48px of the next card peeks — enough to read as "there's
 * more", not so much that it looks like a broken grid.
 *
 * Height is fixed at ~184px with the description clamped to two lines rather
 * than the 300px square in the original sketch: a square is an awkward shape
 * for text-heavy content and would either overflow or truncate hard. The full
 * description is in the trace pane, where there's room. The phone shows the
 * answer; the rail shows the evidence.
 */
export default function SessionCarousel({ sessions, registeredIds, onRegister }) {
  return (
    <div
      className="ses-rail"
      role="region"
      aria-label={`${sessions.length} matching sessions`}
    >
      {sessions.map((s) => (
        <SessionCard
          key={s.id}
          session={s}
          registered={registeredIds?.has(s.id)}
          onRegister={onRegister}
        />
      ))}
    </div>
  );
}

function SessionCard({ session, registered, onRegister }) {
  return (
    <article className="ses-card">
      <header className="ses-top">
        <span className={`ses-type ses-type-${session.type}`}>{session.type}</span>
        <span className="ses-level">{session.level}</span>
      </header>

      <h4 className="ses-title">{session.title}</h4>
      <p className="ses-desc">{session.description}</p>

      <div className="ses-meta">
        <span className="ses-data">
          {formatDate(session.date)} · {formatTime(session.start_time)}
        </span>
        <span className="ses-data">{session.location}</span>
      </div>

      <button
        className={`ses-register ${registered ? "is-registered" : ""}`}
        onClick={() => !registered && onRegister?.(session)}
        disabled={registered}
      >
        {registered ? "Registered" : "Register"}
      </button>
    </article>
  );
}
