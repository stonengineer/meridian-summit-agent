"""
Operating memory of the agent

Logic for the function definitions in `store.py` RecordStore, allows for
runtime manipulation of the data layer by the agent
"""

from datetime import datetime, timezone

from .models import (
	RegistrationStatus,
	RegistrationOutcome,
	SessionRegistration,
	RegistrationResult,
	RegistrationError,
	EntitlementError,
	ConflictError)

_TIER_ORDER = ["Explorer", "Builder", "Summit Executive"]
_MIN_TIER = {
	"keynote": "Explorer",
	"breakout": "Explorer",
	"workshop": "Builder",
	"certification": "Builder",
	"executive": "Summit Executive"
}

class InMemoryStore:
	def __init__(self, attendee, sessions):
		self._attendee = attendee
		self._sessions = {s.id: s for s in sessions}
		self._registrations: dict[str, SessionRegistration] = {}

		now = datetime.now(timezone.utc).isoformat()
		self._r_index = 0
		for s_id in self._attendee.registered_sessions:
			self._r_index += 1
			r_id = f"{self._r_index:03d}"
			self._registrations[r_id] = SessionRegistration(
				id = r_id,
				attendee_id = self._attendee.id,
				session_id = s_id,
				status = RegistrationStatus.REGISTERED,
				created_date = now
			)

	def session_register(
		self,
		session_id: str
	) -> RegistrationResult:
		# ensure valid attendee and session
		session = self._sessions.get(session_id)
		if session is None:
			raise RegistrationError(f"No session with id {session_id!r}")

		# idempotency check
		for r in self._registrations.values():
			if (r.session_id == session_id and 
				r.status != RegistrationStatus.CANCELLED):
				return RegistrationResult(
					registration = r,
					outcome = RegistrationOutcome.ALREADY_REGISTERED)

		# entitlement check
		if not self._tier_allows(self._attendee.pass_tier, session.type):
			raise EntitlementError(
				f"{session.type} sessions require a "
				f"{_MIN_TIER[session.type]} pass or higher; "
				f"attendee holds {self._attendee.pass_tier}."
			)

		# conflict check, brute force since only one attendee
		s_start_time = datetime.combine(
			session.date,
			session.start_time)
		s_end_time: datetime = datetime.combine(
			session.date,
			session.end_time)
		for r in self._registrations.values():
			if r.status == RegistrationStatus.CANCELLED:
				continue
			cmp_session = self._sessions.get(r.session_id)
			if cmp_session is not None:
				cmp_start_time: datetime = datetime.combine(
					cmp_session.date,
					cmp_session.start_time)
				cmp_end_time: datetime = datetime.combine(
					cmp_session.date,
					cmp_session.end_time)
				if s_start_time < cmp_end_time and cmp_start_time < s_end_time:
					raise ConflictError(
						f"Registration conflicts with session {cmp_session.title}")

		# write to dict
		now = datetime.now(timezone.utc).isoformat()
		self._r_index += 1
		r_id = f"{self._r_index:03d}"
		reg = SessionRegistration(
			id = r_id,
			attendee_id = self._attendee.id,
			session_id = session_id,
			status = RegistrationStatus.REGISTERED,
			created_date = now
		)
		self._registrations[r_id] = reg
		return RegistrationResult(
			registration = reg,
			outcome = RegistrationOutcome.CREATED)

	def cancel_registration(
		self,
		registration_id: str
	) -> SessionRegistration | None:
		reg: SessionRegistration | None = self._registrations.get(registration_id)
		if reg is None:
			return None
		if reg.attendee_id != self._attendee.id:
			return None
		reg.status = RegistrationStatus.CANCELLED
		return reg

	def registrations_for(self) -> list[SessionRegistration]:
		return [
			r for r in self._registrations.values() 
			if r.status != RegistrationStatus.CANCELLED]

	def _tier_allows(self, pass_tier: str, session_type: str) -> bool:
		required: str | None = _MIN_TIER.get(session_type)
		if required is None:
			raise EntitlementError(f"Unknown session type: {session_type!r}")
		try:
			return _TIER_ORDER.index(pass_tier) >= _TIER_ORDER.index(required)
		except ValueError:
			raise EntitlementError(f"Unknown pass tier: {pass_tier!r}")
