"""
Hybrid Retriever Registry

Defines a hybrid retriever (or extension) for each loader type defined in
loaders.py. Called by tools.py to expose retriever options to the agent
"""

import os
import random
import logging
from functools import lru_cache

from .retrieval import(
	HybridRetriever,
	AttendeeRetriever,
	Article,
	Attendee,
	Session)
from .records import InMemoryStore, RecordStore
from .loaders import(
	load_articles,
	load_attendees,
	load_sessions)
from .embeddings import get_embed_fn
from .config import get_config

LOGGER = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def get_active_attendee() -> Attendee:
	attendees: list[Attendee] = load_attendees()

	# allow env override for active user selection
	if forced := get_config().active_attendee_id:
		match: Attendee | None = next(
			(a for a in attendees if a.id == forced), None)
		if match is None:
			raise ValueError(f"ACTIVE_ATTENDEE_ID={forced!r} not found")
		LOGGER.info("Active attendee (forced) %s (%s)", match.name, match.id)
		return match

	# if no override, choose random user
	chosen = random.choice(attendees)
	LOGGER.info("Active attendee (random) %s (%s, %s)",
		chosen.name, chosen.id, chosen.pass_tier)
	return chosen

def me_payload() -> dict:
	a: Attendee = get_active_attendee()
	return {
		"id": a.id,
		"name": a.name,
		"first_name": a.first_name,
		"last_name": a.last_name,
		"title": a.title,
		"company": a.company,
		"pass_tier": a.pass_tier,
		"interests": a.interests
	}

@lru_cache(maxsize=1)
def get_store() -> RecordStore:
	return InMemoryStore(get_active_attendee(), load_sessions())

@lru_cache(maxsize=1)
def get_faq_retriever() -> HybridRetriever[Article]:
	return HybridRetriever(load_articles(), get_embed_fn())

@lru_cache(maxsize=1)
def get_attendee_retriever() -> AttendeeRetriever:
	return AttendeeRetriever(load_attendees(), get_embed_fn())

@lru_cache(maxsize=1)
def get_session_retriever() -> HybridRetriever[Session]:
	return HybridRetriever(load_sessions(), get_embed_fn())
