import { useEffect, useRef, useState } from "react";
import AttendeeCard from "./AttendeeCard.jsx";
import OutcomeCard from "./OutcomeCard.jsx";
import RegistrationsCard from "./RegistrationsCard.jsx";
import SessionCarousel from "./SessionCarousel.jsx";
import { cardsFromActivity } from "../lib/cards.js";
import { clockNow, parseName } from "../lib/format.js";
import "./PhoneChat.css";

const PROMPTS = [
  "What's on my schedule?",
  "Any sessions on evaluation?",
  "Who should I talk to about vector infrastructure?",
  "When does registration open?",
];

/**
 * The phone.
 *
 * Framed as the chat surface inside the (unbuilt) Meridian Summit event app —
 * the premise is that the attendee tapped "Ask Cairn" a moment ago and won't
 * leave. So there's no app chrome beyond what sells the frame: a status bar, a
 * chat header with a back affordance that goes nowhere, and a home indicator.
 * The frame is deliberately restrained; a photorealistic bezel would eat ~100px
 * of card room for no demo value.
 */
export default function PhoneChat({
  me,
  messages,
  thinking,
  error,
  registeredIds,
  onSend,
}) {
  const [input, setInput] = useState("");
  const [clock, setClock] = useState(clockNow);
  const scrollRef = useRef(null);

  useEffect(() => {
    const t = setInterval(() => setClock(clockNow()), 30_000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, thinking]);

  function submit(text, display) {
    const value = (text ?? input).trim();
    if (!value || thinking) return;
    setInput("");
    onSend(value, display);
  }

  const first = me ? parseName(me.name).first : null;

  return (
    <div className="phone-stage">
      <div className="phone">
        <div className="phone-status">
          <span className="phone-clock">{clock}</span>
          <span className="phone-icons" aria-hidden="true">
            <i className="ico-sig" />
            <i className="ico-wifi" />
            <i className="ico-batt" />
          </span>
        </div>

        <header className="phone-header">
          <span className="phone-back" aria-hidden="true">
            ‹
          </span>
          <div className="phone-header-id">
            <span className="phone-title">Cairn</span>
            <span className="phone-status-line">Meridian Summit</span>
          </div>
        </header>

        <div className="phone-scroll" ref={scrollRef}>
          {messages.length === 0 && (
            <div className="phone-welcome">
              <div className="welcome-mark" aria-hidden="true">
                ▲
              </div>
              <h1 className="welcome-title">
                {first ? `Welcome, ${first}` : "Welcome"}
              </h1>
              <p className="welcome-copy">
                Ask about sessions, people, or anything about the summit. I'll
                only tell you what's actually in the event data.
              </p>
              <div className="welcome-prompts">
                {PROMPTS.map((p) => (
                  <button key={p} className="prompt" onClick={() => submit(p)}>
                    {p}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <Message
              key={i}
              message={m}
              registeredIds={registeredIds}
              onRegister={(s) =>
                submit(
                  // Agent gets the id so it needn't re-search; user sees prose.
                  `Register me for session ${s.id} ("${s.title}").`,
                  `Register me for ${s.title}`
                )
              }
            />
          ))}

          {thinking && (
            <div className="row row-agent">
              <div className="bubble bubble-agent">
                <div className="typing">
                  <span />
                  <span />
                  <span />
                </div>
              </div>
            </div>
          )}

          {error && <div className="phone-error">{error}</div>}
        </div>

        <div className="phone-composer">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submit()}
            placeholder="Ask Cairn…"
            aria-label="Message Cairn"
            disabled={thinking}
          />
          <button
            className="send"
            onClick={() => submit()}
            disabled={thinking || !input.trim()}
            aria-label="Send"
          >
            ↑
          </button>
        </div>

        <div className="phone-home" aria-hidden="true" />
      </div>
    </div>
  );
}

function Message({ message, registeredIds, onRegister }) {
  if (message.role === "user") {
    return (
      <div className="row row-user">
        <div className="bubble bubble-user">{message.content}</div>
      </div>
    );
  }

  const cards = cardsFromActivity(message.activity);

  return (
    <div className="row row-agent">
      <div className="agent-stack">
        {message.content && (
          <div className="bubble bubble-agent">
            {message.content}
            {message.offline && <span className="offline-tag">offline</span>}
          </div>
        )}
        {cards.map((card, i) => (
          <Card
            key={i}
            card={card}
            registeredIds={registeredIds}
            onRegister={onRegister}
          />
        ))}
      </div>
    </div>
  );
}

function Card({ card, registeredIds, onRegister }) {
  switch (card.kind) {
    case "attendees":
      return (
        <div className="card-stack">
          {card.people.map((p) => (
            <AttendeeCard key={p.id} person={p} />
          ))}
        </div>
      );
    case "sessions":
      return (
        <SessionCarousel
          sessions={card.sessions}
          registeredIds={registeredIds}
          onRegister={onRegister}
        />
      );
    case "registrations":
      return <RegistrationsCard registrations={card.registrations} />;
    case "outcome":
      return <OutcomeCard result={card.result} />;
    default:
      return null;
  }
}
