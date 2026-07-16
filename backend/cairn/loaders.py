"""
Data Loaders (from JSON static files)

Defines typed dataclasses used for importing the JSON source data from inside
the `./data/` directory. Used by registry.py to define the hybrid retrievers
"""

import json
from .retrieval import Article, Attendee, Session
from datetime import date, time
from .paths import DATA_DIR

def load_articles() -> list[Article]:
	raw = json.loads((DATA_DIR / "knowledge_base.json").read_text())
	return [Article(
		id = a["id"],
		category = a["category"],
		question = a["question"],
		content = a["content"]
	) for a in raw["faqs"]]

def load_attendees() -> list[Attendee]:
	raw = json.loads((DATA_DIR / "attendees.json").read_text())
	return [Attendee(
		id = a["id"],
		name = a["name"],
		first_name = a["first_name"],
		last_name = a["last_name"],
		title = a["title"],
		company = a["company"],
		email = a["email"],
		phone = a["phone"],
		is_speaker = a["is_speaker"],
		profile = a["profile"],
		interests = a["interests"],
		pass_tier = a["pass_tier"],
		registered_sessions = a["registered_sessions"]
	) for a in raw["attendees"]]

def load_sessions() -> list[Session]:
	raw = json.loads((DATA_DIR / "sessions.json").read_text())
	return [Session(
		id = s["id"],
		title = s["title"],
		type = s["type"],
		description = s["description"],
		speaker_ids = s["speaker_ids"],
		date = date.fromisoformat(s["date"]),
		start_time = time.fromisoformat(s["start_time"]),
		end_time = time.fromisoformat(s["end_time"]),
		location = s["location"],
		tags = s["tags"],
		level = s["level"]
	) for s in raw["sessions"]]