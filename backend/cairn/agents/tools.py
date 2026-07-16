"""
Tools available to the agent to perform user requests

Includes configured hybrid retriever actions to assist with searching Attendees,
Sessions, and FAQ data. 

If the Agent instance includes an authentication token
(abstracted to an Attendee ID for demo simplicity) the Agent actions will affect
the database on behalf of that Attendee.
Database actions include:
* Register for a session
* Unenroll from a session
* List their current registrations
"""

from __future__ import annotations

from vertexai.generative_models import FunctionDeclaration, Tool

from ..retrieval import ScoredResult
from ..records.models import RegistrationStatus, RegistrationOutcome
from ..records import RegistrationError, SessionRegistration, RegistrationResult
from ..registry import(
	me_payload,
	get_store,
	get_faq_retriever,
	get_attendee_retriever,
	get_session_retriever)

def whoami() -> dict:
	return me_payload()

def search_faq(query: str) -> list[dict]:
	results: list[ScoredResult] = get_faq_retriever().retrieve(query)
	return [{
		"id": r.item.id,
		"question": r.item.question,
		"content": r.item.content,
		"score": round(r.hybrid_score, 4)
	} for r in results]

def find_attendees(
	query: str, 
	email_domain: str | None = None,
	company: str | None = None
) -> list[dict]:
	results: list[ScoredResult] = get_attendee_retriever().retrieve(
		query,
		email_domain = email_domain,
		company = company)
	return [{
		"id": r.item.id,
		"name": r.item.name,
		"title": r.item.title,
		"company": r.item.company,
		"is_speaker": r.item.is_speaker,
		"profile": r.item.profile,
		"phone": r.item.phone,
		"email": r.item.email
	} for r in results]

def find_sessions(query: str) -> list[dict]:
	results: list[ScoredResult] = get_session_retriever().retrieve(query)
	return [{
		"id": r.item.id,
		"title": r.item.title,
		"type": r.item.type,
		"description": r.item.description,
		"date": r.item.date.isoformat(),
		"start_time": r.item.start_time.strftime("%H:%M"),
		"end_time": r.item.end_time.strftime("%H:%M"),
		"location": r.item.location,
		"level": r.item.level
	} for r in results]

def register_for_session(session_id: str) -> dict:
	try:
		result = get_store().session_register(session_id)
		return {
			"ok": True,
			"outcome": result.outcome.value,
			"registration_id": result.registration.id,
			"status": result.registration.status.value,
			"message": (
				"You were already registered for this session."
				if result.outcome == RegistrationOutcome.ALREADY_REGISTERED
				else "Registration complete"
			)
		}
	except RegistrationError as e:
		return {
			"ok": False,
			"message": str(e)
		}

def cancel_registration(registration_id: str) -> dict:
	reg = get_store().cancel_registration(registration_id)
	if reg is None:
		return {
			"ok": False,
			"message": "No registration found with that ID."
		}
	return {
		"ok": True,
		"registration_id": reg.id,
		"status": reg.status.value,
		"message": "Registration cancellation complete"
	}

def my_registrations() -> dict:
	registrations = get_store().registrations_for()
	r_session_ids: set[str] = {r.session_id for r in registrations}
	r_sessions = {s.id: s 
		for s in get_session_retriever().items
		if s.id in r_session_ids}
	return {
		"registrations": [
			{
				"registration_id": r.id,
				"session_id": r.session_id,
				"session_title": r_sessions[r.session_id].title,
				"status": r.status.value
			}
			for r in registrations
		]
	}

TOOL_DECLARATIONS: list[FunctionDeclaration] = [
	FunctionDeclaration(
		name="whoami",
		description=(
			"Get the identity of the attendee you are assisting: their name, title, "
			"company, pass tier, and interests. Call this when you need to "
			"personalize a recommendation or when the user asks who they are logged "
			"in as. All registration actions are taken on this person's behalf."
		),
		parameters={"type": "object", "properties": {}},
	),
	FunctionDeclaration(
		name="search_faq",
		description=(
			"Search the event FAQ and policy knowledge base for Meridian Summit: "
			"registration and pass tiers, venue and rooms, daily schedule, food, "
			"travel, the expo floor, certification, the mobile app, accessibility, "
			"and the code of conduct. Use for questions about the event itself "
			"(what/when/where/how), not for finding people or specific sessions."
		),
		parameters={
			"type": "object",
			"properties": {
				"query": {
					"type": "string",
					"description":
						"Natural-language question, e.g. 'when does registration open?'",
				}
			},
			"required": ["query"],
		},
	),
	FunctionDeclaration(
		name="find_sessions",
		description=(
			"Search the session catalog (keynotes, breakouts, workshops) by topic, "
			"theme, or interest. Use when the user wants talks or workshops about a "
			"subject, e.g. 'any good sessions on evaluation?'. Returns session IDs "
			"needed for registration."
		),
		parameters={
			"type": "object",
			"properties": {
				"query": {
					"type": "string",
					"description": 
						"Topic or interest, e.g. 'hybrid retrieval', 'security'",
				}
			},
			"required": ["query"],
		},
	),
	FunctionDeclaration(
		name="find_attendees",
		description=(
			"Find attendees or speakers by expertise, role, company, or interest. "
			"Use for 'who should I talk to about X', 'who works on Y', or to look up "
			"a specific person by name or email. Optional filters narrow to an exact "
			"email domain or company."
		),
		parameters={
			"type": "object",
			"properties": {
				"query": {
					"type": "string",
					"description": (
						"Semantic search over expertise, role, and profile — e.g. "
						"'applied AI', 'vector infrastructure'. Pass a full email "
						"address here for an exact lookup of one person."
					),
				},
				"email_domain": {
					"type": "string",
					"description": 
						("Filter to this email domain only, e.g. 'google.com'. "
						"Omit unless the user constrains by domain."),
				},
				"company": {
					"type": "string",
					"description": 
						("Filter to this company only, e.g. 'Northwind Financial'. "
						"Omit unless the user constrains by company."),
				},
			},
			"required": ["query"],
		},
	),
	FunctionDeclaration(
		name="my_registrations",
		description=(
			"List the sessions the current attendee is registered for, with each "
			"registration's ID and status. Call this before cancelling, to get the "
			"registration_id, or when the user asks about their schedule."
		),
		parameters={"type": "object", "properties": {}},
	),
	FunctionDeclaration(
		name="register_for_session",
		description=(
			"Register the current attendee for a session. Requires a session_id from "
			"find_sessions. May be refused if their pass tier doesn't permit the "
			"session type or if it conflicts with an existing registration — the "
			"response explains why. Registering twice is safe and returns the "
			"existing registration."
		),
		parameters={
			"type": "object",
			"properties": {
				"session_id": {
					"type": "string",
					"description": "Session ID in the form 'ses-002', from find_sessions",
				}
			},
			"required": ["session_id"],
		},
	),
	FunctionDeclaration(
		name="cancel_registration",
		description=(
			"Cancel one of the current attendee's registrations. Requires a "
			"registration_id from my_registrations — this is NOT a session_id."
		),
		parameters={
			"type": "object",
			"properties": {
				"registration_id": {
					"type": "string",
					"description": "Registration ID from my_registrations, e.g. '003'",
				}
			},
			"required": ["registration_id"],
		},
	),
]

CONFERENCE_TOOLS = Tool(function_declarations=TOOL_DECLARATIONS)

TOOL_IMPL = {
	"whoami": lambda a: whoami(),
	"search_faq": lambda a: {"results": search_faq(a["query"])},
	"find_sessions": lambda a: {"results": find_sessions(a["query"])},
	"find_attendees": lambda a: {
		"results": find_attendees(
			a["query"],
			email_domain=a.get("email_domain"),
			company=a.get("company")
		)},
	"my_registrations": lambda a: my_registrations(),
	"register_for_session": lambda a: register_for_session(a["session_id"]),
	"cancel_registration": lambda a: cancel_registration(a["registration_id"]),
}
