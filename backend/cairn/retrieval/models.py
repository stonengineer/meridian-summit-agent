"""
Domain models for data retrievers

Each model corresponds to a searchable file type in the ./data/ directory, and
must satisfy the `Searchable` shape definition to be utilized. Each model may
define its own `searchable_text` to showcase what needs to be searched on.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_type, time as time_type

# FAQ Article definition
@dataclass
class Article:
	id: str
	category: str
	question: str
	content: str

	@property
	def searchable_text(self) -> str:
		return f"{self.question}. {self.content}"

# Event Attendee definition
@dataclass
class Attendee:
	id: str
	name: str
	first_name: str
	last_name: str
	title: str
	company: str
	email: str
	phone: str
	is_speaker: bool
	profile: str
	interests: list[str]
	pass_tier: str
	registered_sessions: list[str]

	@property
	def searchable_text(self) -> str:
		return (
			f"{self.name} "
			f"({self.title} at {self.company}). "
			f"Is Event Speaker: {self.is_speaker}; "
			f"{self.profile}; "
			f"Interests: {', '.join(self.interests)}"
		)

# Event Session definition
@dataclass
class Session:
	id: str
	title: str
	type: str
	description: str
	speaker_ids: list[str]
	date: date_type
	start_time: time_type
	end_time: time_type
	location: str
	tags: list[str]
	level: str

	@property
	def searchable_text(self) -> str:
		return (
			f"{self.title} - {self.type}"
			f"{self.description}"
			f"{self.date} {self.start_time}-{self.end_time}"
			f"{self.location}"
			f"Level: {self.level}"
			f"Tags: ({', '.join(self.tags)})"
		)