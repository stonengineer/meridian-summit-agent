"""Config file to import Vertex if available"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

def _flag(name: str, default: bool = False) -> bool:
	raw = os.getenv(name)
	if raw is None:
		return default
	return raw.strip().lower() in ("1", "true", "yes", "on")

@dataclass(frozen=True)
class Config:
	use_vertex: bool
	gcp_project_id: str | None
	gcp_region: str
	gemini_model: str
	embedding_model: str
	active_attendee_id: str | None
	cors_origins: list[str]

	def validate(self) -> None:
		if self.use_vertex and not self.gcp_project_id:
			raise RuntimeError("USE_VERTEX=true but GCP_PROJECT_ID is unset.")

@lru_cache(maxsize=1)
def get_config() -> Config:
	return Config(
		use_vertex = _flag("USE_VERTEX"),
		gcp_project_id = os.getenv("GCP_PROJECT_ID"),
		gcp_region = os.getenv("GCP_REGION", "us-central1"),
		gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
		embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-005"),
		active_attendee_id = os.getenv("ACTIVE_ATTENDEE_ID"),
		cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
	)