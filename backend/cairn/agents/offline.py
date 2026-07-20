"""
Offline fallback router — demo insurance, not a second brain.

When Vertex is unavailable, this keeps Cairn answering by faking the ONE thing
Gemini does that we can cheaply approximate: deciding which tool to call.
Everything downstream — hybrid retrieval, the store, the real corpus — is the
same code the online path uses. Only routing and phrasing are hand-rolled.

Deliberately READ-ONLY. It routes to the three retrievers, whoami, and
my_registrations, never to register/cancel. A mis-routed read is a wrong
answer; a mis-routed write is a corrupted demo.

Scope of the lie — this does keyword matching, not reasoning. It cannot handle:
  * multi-step questions ("find a security session and check for conflicts")
  * pronoun resolution ("is she speaking?")
  * synthesis across corpora
It answers one question with one tool. Routing accuracy is ~25/26 on the
utterances in tests/test_offline_routing.py; unmatched input falls through to
FAQ search, which is the broadest corpus and the safest default.
"""

from __future__ import annotations

import logging
import re

from .tools import (
	find_attendees,
	find_sessions,
	my_registrations,
	search_faq,
	whoami,
)

LOGGER = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# Intent patterns. Checked in the order listed in _route(); first match wins,
# so the most specific intents come first.
# --------------------------------------------------------------------------

# "who am I", "what's my tier" — identity, NOT schedule.
# Note: deliberately excludes a bare "my pass", which collides with the FAQ
# question "can I upgrade my pass?".
_WHOAMI = re.compile(
	r"\bwho am i\b|\bwhat'?s my (name|pass tier|tier|title|company)\b|"
	r"\bmy (badge|profile)\b|\bam i a speaker\b",
	re.I,
)

# "my schedule", "what am I registered for".
# Uses [\s\w']* rather than .* between the two groups: `.*` cannot match the
# zero-width gap in "my schedule", where both \b anchors sit on the same space.
_SELF_SCHEDULE = re.compile(
	r"\b(my|i'?m|am i)\b[\s\w']*\b(schedul\w*|registrat\w*|registered|signed up|"
	r"agenda|booked|enrolled|attending)\b|\bwhat am i\b|\bmy sessions?\b",
	re.I,
)

# People: role/expertise questions, company mentions, email addresses.
_PEOPLE = re.compile(
	r"\bwho (should|do|can|else|is|are|works?|knows?)\b|\btalk to\b|\bmeet\b|"
	r"\banyone\b|\bsomeone\b|\bpeople\b|\battendees?\b|\bspeakers?\b|"
	r"\bexperts?\b|"
	r"\bfrom (google|northwind|meridian|fortress|aperture|helios|cascade|sterling|loop)\b|"
	r"[\w.+-]+@[\w-]+\.[\w.]+",
	re.I,
)

# "tell me about Lena Warsaw" — CASE-SENSITIVE on purpose. With re.I, [A-Z][a-z]+
# matches any word, so "anything about hybrid retrieval" would route to people.
_PROPER_NAME = re.compile(
	r"\b(?:tell me about|find|look ?up|about)\s+[A-Z][a-z]+\s+[A-Z][a-z]+"
)

_SESSIONS = re.compile(
	r"\bsessions?\b|\btalks?\b|\bworkshops?\b|\bkeynotes?\b|\bbreakouts?\b|"
	r"\bpresentations?\b|\blabs?\b|\bwhat'?s on\b|\banything (on|about)\b",
	re.I,
)

_FAQ = re.compile(
	r"\bregistration\b|\bpass(es)?\b|\btier\b|\bvenue\b|\bmoscone\b|\broom\b|"
	r"\bwifi\b|\bfood\b|\blunch\b|\bbreakfast\b|\bdiet\b|\bshuttle\b|\bhotel\b|"
	r"\bparking\b|\bbart\b|\bairport\b|\bexpo\b|\bbooth\b|\bcertification\b|"
	r"\bexam\b|\bapp\b|\baccessib\b|\bcode of conduct\b|\bpolicy\b|\brefund\b|"
	r"\bcancel(lation)?\b|\bupgrade\b|\btransfer\b|\bbadge\b|\blost\b|\bhours?\b|"
	r"\bopen\b|\bclose\b|\bwhen does\b|\bwhere (is|are|do)\b|\bhow (do|much|long)\b",
	re.I,
)


def offline_turn(message: str) -> dict:
	"""Route one message to one tool and template a reply from real results."""
	text = message.strip()
	intent, result = _route(text)
	LOGGER.info("[offline] routed %r -> %s", text[:60], intent)

	tool_activity: list[dict] = []
	if intent is not None:
		tool_activity.append({"tool": intent, "args": {"query": text}, "result": result})

	return {
		"answer": _render(intent, result),
		"tool_activity": tool_activity,
		"offline": True,
	}


def _route(text: str) -> tuple[str | None, object]:
	"""Pick exactly one tool. Order is the priority."""
	if _WHOAMI.search(text):
		return "whoami", whoami()

	if _SELF_SCHEDULE.search(text):
		return "my_registrations", my_registrations()

	# People before sessions: "who's speaking about security" is a people
	# question, and _SESSIONS would otherwise claim it.
	if _PEOPLE.search(text) or _PROPER_NAME.search(text):
		return "find_attendees", {"results": find_attendees(text)}

	if _SESSIONS.search(text):
		return "find_sessions", {"results": find_sessions(text)}

	if _FAQ.search(text):
		return "search_faq", {"results": search_faq(text)}

	# Unmatched: FAQ is the broadest corpus and the safest default.
	results = search_faq(text)
	return ("search_faq", {"results": results}) if results else (None, None)


def _render(intent: str | None, result) -> str:
	"""Template an answer from real tool output. No LLM, no invention."""
	if intent is None:
		return (
			"I couldn't find anything on that in the event data. Try asking about "
			"sessions, attendees, or event logistics."
		)

	if intent == "whoami":
		me = result
		speaking = " You're speaking at this event." if me.get("is_speaker") else ""
		return (
			f"You're {me['name']}, {me['title']} at {me['company']}, "
			f"on a {me['pass_tier']} pass.{speaking}"
		)

	if intent == "my_registrations":
		regs = result.get("registrations", [])
		if not regs:
			return "You're not registered for any sessions yet."
		return f"You're registered for {len(regs)} session{'s' if len(regs) != 1 else ''}:"

	if intent == "find_attendees":
		people = result.get("results", [])
		if not people:
			return "I couldn't find anyone matching that."
		return "Here's who matches:\n\n"

	if intent == "find_sessions":
		sessions = result.get("results", [])
		if not sessions:
			return "I couldn't find a session on that."
		return "These look relevant:\n\n"

	if intent == "search_faq":
		faqs = result.get("results", [])
		if not faqs:
			return "I don't have anything on that in the event FAQ."
		top = faqs[0]
		return f"{top['content']}\n\n (From: {top['question']})"

	return "Something went wrong routing that question."
