"""
Object models for the operating memory of the agent

Holds registration data for sessions, which can be modified during the agent
workflow processes, and different error types
"""

from dataclasses import dataclass
from typing import Literal
from enum import Enum

class RegistrationStatus(str, Enum):
	REGISTERED = "registered"
	WAITLIST = "waitlist"
	CANCELLED = "cancelled"

class RegistrationOutcome(str, Enum):
	CREATED = "created"
	ALREADY_REGISTERED = "already_registered"
	WAITLISTED = "waitlisted"

@dataclass
class SessionRegistration:
	id: str
	attendee_id: str
	session_id: str
	status: RegistrationStatus
	created_date: str

@dataclass
class RegistrationResult:
	registration: SessionRegistration
	outcome: RegistrationOutcome

class RegistrationError(Exception):
	"""Base for refusals the agent should explain to the user"""

class EntitlementError(RegistrationError):
	"""Pass tier does not permit this session type"""

class ConflictError(RegistrationError):
	"""Overlaps an existing registration"""
