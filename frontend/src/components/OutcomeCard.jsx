import "./OutcomeCard.css";

/**
 * The result of a write — register or cancel.
 *
 * This is the card that makes the store's business rules visible. An
 * entitlement refusal ("workshop sessions require a Builder pass or higher;
 * attendee holds Explorer") is the single most demonstrative thing in the
 * build: it proves the rules live in deterministic code, not in the prompt.
 * So refusals get the reserved --clay accent and are never hidden.
 *
 * Copy note: the card states what happened, in the interface's voice. It does
 * not apologise and it is not vague. The backend already wrote the message —
 * we render it rather than inventing our own phrasing on top.
 */
export default function OutcomeCard({ result }) {
  const ok = result.ok === true;
  const already = result.outcome === "already_registered";
  const waitlisted = result.status === "waitlist";

  return (
    <article className={`out-card ${ok ? "is-ok" : "is-refused"}`}>
      <div className="out-head">
        <span className="out-mark" aria-hidden="true">
          {ok ? (already ? "=" : "✓") : "!"}
        </span>
        <span className="out-label">
          {!ok
            ? "Not registered"
            : already
              ? "Already registered"
              : waitlisted
                ? "Added to waitlist"
                : "Registered"}
        </span>
      </div>

      <p className="out-msg">{result.message}</p>

      {result.registration_id && (
        <div className="out-ref">
          <span className="out-ref-key">registration</span>
          <code className="out-ref-val">{result.registration_id}</code>
        </div>
      )}
    </article>
  );
}
