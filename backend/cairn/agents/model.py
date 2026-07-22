"""
Loads the Reasoning Engine LLM

Leverages environment variables to either load/initialize a Vertex-backed
google.genai.Client, or return None on error/disabled.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from ..config import get_config, Config

LOGGER = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def get_model():
	cfg: Config = get_config()
	if not cfg.use_vertex:
		return None
	try:
		from google import genai
		return genai.Client(
			vertexai = True,
			project = cfg.gcp_project_id,
			location = cfg.gcp_region
		)
	except KeyError as e:
		LOGGER.warning("[model] missing env var: %s", e)
		return None
	except Exception:
		LOGGER.warning("[model] Gemini init failed", exc_info=True)
		return None
