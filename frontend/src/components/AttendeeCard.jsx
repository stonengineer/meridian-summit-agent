import { avatarStyle, parseName } from "../lib/format.js";
import "./AttendeeCard.css";

/**
 * Compact directory card. Attendees are a *lookup* — you want to identify the
 * person and reach them, not read an essay. So: avatar, name, one line of
 * context, three actions. The full profile prose lives in the trace pane.
 *
 * Contact buttons render from optional fields. find_attendees currently returns
 * name/title/company/is_speaker/profile and no contact details, so today only
 * the disabled state shows. Add `email`/`phone` to the tool's return dict and
 * the buttons light up with no change here.
 */
export default function AttendeeCard({ person }) {
  const { initials } = parseName(person.name);
  const { phone, email } = person;

  return (
    <article className="att-card">
      <div className="att-head">
        <div className="att-avatar" style={avatarStyle(person.id)} aria-hidden="true">
          {initials}
        </div>
        <div className="att-id">
          <div className="att-name">
            {person.name}
            {person.is_speaker && <span className="att-speaker">Speaker</span>}
          </div>
          <div className="att-role">
            {person.title} · {person.company}
          </div>
        </div>
      </div>

      <div className="att-actions">
        <ContactButton
          label="Call"
          href={phone ? `tel:${phone}` : null}
          hint="No phone on file"
        />
        <ContactButton
          label="Message"
          href={phone ? `sms:${phone}` : null}
          hint="No phone on file"
        />
        <ContactButton
          label="Email"
          href={email ? `mailto:${email}` : null}
          hint="No email on file"
        />
      </div>
    </article>
  );
}

/**
 * A link when we can act, a disabled control when we can't — never a button
 * that looks live and does nothing when tapped.
 */
function ContactButton({ label, href, hint }) {
  if (!href) {
    return (
      <button className="att-btn" disabled title={hint} aria-label={`${label} — ${hint}`}>
        {label}
      </button>
    );
  }
  return (
    <a className="att-btn att-btn-live" href={href}>
      {label}
    </a>
  );
}
