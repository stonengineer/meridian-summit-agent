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
from ..config import get_config, Config

LOGGER = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def get_model():
	cfg: Config = get_config()
	if not cfg.use_vertex:
		return None
	try:
		import vertexai
		from vertexai.generative_models import GenerativeModel

		vertexai.init(
			project = cfg.gcp_project_id,
			location = cfg.gcp_region
		)
		return GenerativeModel(
			cfg.gemini_model,
			system_instruction = SYSTEM_PROMPT,
			tools = [CONFERENCE_TOOLS]
		)
	except KeyError as e:
		LOGGER.warning("[model] missing env var: %s", e)
		return None
	except Exception:
		LOGGER.warning("[model] Gemini init failed", exc_info=True)
		return None
