import { formatDate, formatTime } from "../lib/format.js";
import "./RegistrationsCard.css";

/**
 * The attendee's own schedule.
 *
 * A list, not a carousel — this is a thing you scan top-to-bottom, and the
 * registration id matters (it's what cancel needs), so it's shown rather than
 * hidden. Empty state is an invitation to act, not an apology.
 */
export default function RegistrationsCard({ registrations }) {
  if (!registrations.length) {
    return (
      <article className="reg-card reg-empty">
        Nothing on your schedule yet. Ask about sessions to find something.
      </article>
    );
  }

  return (
    <article className="reg-card">
      {registrations.map((r) => (
        <div className="reg-row" key={r.registration_id}>
          <div className="reg-main">
            <div className="reg-title">{r.session_title}</div>
						<span className="reg-when">
							{formatDate(r.date)} · {formatTime(r.start_time)} - {formatTime(r.end_time)}
						</span>
          </div>
          <span className={`reg-status reg-${r.status}`}>{r.status}</span>
        </div>
      ))}
    </article>
  );
}
