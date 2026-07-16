"""
Protocol definition for Session Registration

Session Register: sign yourself up for a session
Cancel Registration: cancel a registration you own
Registrations For: return a list of your registrations (and statuses)
"""

from typing import Protocol
from .models import SessionRegistration, RegistrationResult

class RecordStore(Protocol):
	def session_register(
		self,
		session_id: str) -> RegistrationResult: ...
	def cancel_registration(
		self,
		registration_id: str) -> SessionRegistration | None: ...
	def registrations_for(self) -> list[SessionRegistration]: ...
