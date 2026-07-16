import "./CairnStack.css";

/**
 * The signature element.
 *
 * A cairn is a stack of stones that marks a trail where the path isn't obvious
 * — placed by people who came before, for people coming after. That's the
 * product metaphor, so here it's literal and functional: one stone per tool
 * call in the current turn. You can read at a glance how much work a question
 * took. While the agent is thinking, the stack breathes.
 *
 * It encodes something true (work done), rather than decorating. Capped at five
 * stones because past that it stops being readable and becomes a bar chart.
 */
export default function CairnStack({ count, thinking }) {
  const stones = Math.min(count, 5);

  return (
    <div
      className={`cairn ${thinking ? "is-thinking" : ""}`}
      role="img"
      aria-label={
        thinking
          ? "Working"
          : count === 0
            ? "No tools used this turn"
            : `${count} tool ${count === 1 ? "call" : "calls"} this turn`
      }
    >
      {[...Array(5)].map((_, i) => {
        // Bottom stone is index 4 — build from the ground up.
        const level = 4 - i;
        return (
          <span
            key={i}
            className={`stone stone-${level} ${level < stones ? "is-set" : ""}`}
            style={{ animationDelay: `${level * 0.12}s` }}
          />
        );
      })}
    </div>
  );
}
