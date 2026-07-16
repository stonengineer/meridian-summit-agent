"""
Agent orchestration

Flow per turn:
  1. Call Gemini with the system prompt + tool declarations
     (search_faq, search_sessions, find_attendees, get_session, ...).
  2. Gemini decides which tool(s) to call based on the question.
  3. Execute tool calls, feed results back.
  4. Loop until Gemini produces a final answer.
  5. Return answer + whichever tool results were used, so the UI
     renders the right cards (FAQ citations, session cards, or people).

If Vertex/Gemini is unavailable, a deterministic rule-based fallback
keeps the demo fully functional offline. The fallback is intentionally
simple: it exists so the app never hard-fails in a demo
"""

from __future__ import annotations

import logging
from typing import Optional

from .tools import CONFERENCE_TOOLS, TOOL_IMPL
from .system_prompt import SYSTEM_PROMPT
from .model import get_model
from .offline import offline_turn

_LOOP_CAP = 8
LOGGER = logging.getLogger(__name__)

def run_turn(message: str, history: Optional[list[dict]] = None) -> dict:
	model = get_model()
	if model is None:
		return offline_turn(message)
	return _gemini_answer(model, message, history)

def _gemini_answer(model, message: str, history: list[dict] | None) -> dict:
	from vertexai.generative_models import Content, Part

	chat = model.start_chat(history=_to_gemini_history(history))
	utterance: str = f"## USER UTTERANCE\n\n{message}"
	tool_activity: list[dict] = []

	resp = chat.send_message(utterance)

	for _ in range(_LOOP_CAP): # can make 8 moves before we cut it off
		calls = _extract_function_calls(resp)
		if not calls:
			break
		tool_responses = []
		for call in calls:
			impl = TOOL_IMPL.get(call["name"])
			output = impl(call["args"]) if impl else {"error": "unknown tool"}
			tool_activity.append({
				"tool": call["name"],
				"args": call["args"],
				"result": output
			})
			tool_responses.append(Part.from_function_response(
				name = call["name"],
				response = {"result": output}
			))
		resp = chat.send_message(Content(
			role = "user",
			parts = tool_responses
		))
	else:
		LOGGER.warning("Tool loop hit cap of %d without a final answer", _LOOP_CAP)
		return {
			"answer": "I wasn't able to finish that, could you narrow the request?",
			"tool_activity": tool_activity
		}

	return {
		"answer": _extract_text(resp),
		"tool_activity": tool_activity
	}

def _to_gemini_history(history: list[dict] | None):
	from vertexai.generative_models import Content, Part

	gemini_history = []
	if history is not None:
		for turn in history:
			role = "model" if turn.get("role") == "assistant" else "user"
			gemini_history.append(Content(
				role = role,
				parts = [Part.from_text(turn.get("content", ""))]
			))
	return gemini_history

def _extract_function_calls(resp) -> list[dict]:
	calls = []
	try:
		for part in resp.candidates[0].content.parts:
			fc = getattr(part, "function_call", None)
			if fc and fc.name:
				calls.append({"name": fc.name, "args": dict(fc.args)})
	except (IndexError, AttributeError):
		pass
	return calls

def _extract_text(resp) -> str:
	try:
		parts = resp.candidates[0].content.parts
		return "".join(getattr(p, "text", "") for p in parts).strip()
	except (IndexError, AttributeError):
		return ""
