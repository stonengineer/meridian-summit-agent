"""
Retriever specifc to Attendee records

Features an exact identifier short-circuit for retrieving attendees by their
full email address without ranking - just return that person if they're found.
Includes additional hard constraint filters before sending data to the hybrid
retriever.
"""

from __future__ import annotations

import re
from typing import Optional

from .hybrid_retriever import HybridRetriever, ScoredResult
from .models import Attendee

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

class AttendeeRetriever(HybridRetriever[Attendee]):
	def __init__(self, items: list[Attendee], embed, *, top_k: int=6):
		super().__init__(items, embed, top_k=top_k)
		self._by_email = {a.email.lower(): a for a in items}

	def retrieve(
		self,
		query: str,
		top_k: Optional[int] = None,
		*,
		email_domain: Optional[str] = None,
		company: Optional[str] = None
	) -> list[ScoredResult[Attendee]]:
		q = query.strip()

		# test 1: email short-circuit
		if _EMAIL_RE.match(q):
			hit = self._by_email.get(q.lower())
			return [ScoredResult(item=hit, hybrid_score=1.0)] if hit else []

		# test 2: structured filters exist
		if email_domain or company:
			matching_attendees = [
				a for a in self.items
				if self._passes_filters(a, email_domain, company)
			]
			if not matching_attendees:
				return []
			scoped_retriever = HybridRetriever(
				matching_attendees, 
				self.embed, 
				top_k=self.top_k
			)
			return scoped_retriever.retrieve(q or " ", top_k=top_k)

		# default behavior, regular hybrid search
		return super().retrieve(q, top_k=top_k)

	@staticmethod
	def _passes_filters(
		a: Attendee,
		email_domain: Optional[str] = None,
		company: Optional[str] = None
	) -> bool:
		if email_domain:
			domain = email_domain.lstrip("@").lower()
			if not a.email or not a.email.lower().endswith("@" + domain):
				return False
		if company:
			if not a.company or company.lower() not in a.company.lower():
				return False
		return True
