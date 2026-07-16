"""
Reusable interface used to define searchable data types

Simply needs an identity and blob of text to index; it imports nothing from the
domain models, but those models must extend this shape.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

@runtime_checkable
class Searchable(Protocol):
	id: str

	@property # Generic text blob def that is tokenized or embedded
	def searchable_text(self) -> str: ...
