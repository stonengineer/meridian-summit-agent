"""
Loads the Reasoning Engine LLM

Leverages environment variables to either load/initialize an instance of Gemini
Flash 3.5, or returns None on error/disabled.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache

from .system_prompt import SYSTEM_PROMPT
from .tools import CONFERENCE_TOOLS

LOGGER = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def get_model():
	if os.getenv("USE_VERTEX", "").lower() not in ("1", "true", "yes"):
		return None
	try:
		import vertexai
		from vertexai.generative_models import GenerativeModel

		vertexai.init(
			project = os.environ["GCP_PROJECT_ID"],
			location = os.getenv("GCP_REGION", "us-central1")
		)
		return GenerativeModel(
			os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
			system_instruction = SYSTEM_PROMPT,
			tools = [CONFERENCE_TOOLS]
		)
	except KeyError as e:
		LOGGER.warning("[model] missing env var: %s", e)
		return None
	except Exception:
		LOGGER.warning("[model] Gemini init failed", exc_info=True)
		return None
