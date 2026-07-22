"""
Embedding Function definitions

Based on the environment variables, select the embedding function for the
hybrid retrievers to use
"""

import re
import logging

from .retrieval.hybrid_retriever import Embedder
from .config import get_config, Config

LOGGER = logging.getLogger(__name__)
_TOKEN_RE = re.compile(r"[a-z0-9]+")

def get_embed_fn() -> Embedder:
	cfg: Config = get_config()
	if not cfg.use_vertex:
		return _HashEmbedder()
	client = _try_init_vertex(cfg)
	if client is None:
		LOGGER.warning(
			"[embeddings] Vertex requested but unavailable; using offline fallback")
		return _HashEmbedder()
	return _VertexEmbedder(client, cfg.embedding_model)

def _try_init_vertex(cfg: Config):
	try:
		from google import genai
		return genai.Client(
			vertexai = True,
			project = cfg.gcp_project_id,
			location = cfg.gcp_region
		)
	except Exception:
		LOGGER.warning("[embeddings] Vertex init failed", exc_info=True)
		return None

class _HashEmbedder:
	def __init__(self, dims: int = 256):
		self.dims = dims

	def __call__(self, text: str) -> list[float]:
		# offline mock embed method (keyword histogram)
		vec = [0.0] * self.dims
		for tok in _TOKEN_RE.findall(text.lower()):
			vec[hash(tok) % self.dims] += 1.0
		return vec

	def embed_batch(self, texts: list[str]) -> list[list[float]]:
		return [self(t) for t in texts]

class _VertexEmbedder:
	_MAX_BATCH = 250

	def __init__(self, client, model_name: str):
		self._client = client
		self._model = model_name

	def __call__(self, text: str) -> list[float]:
		resp = self._client.models.embed_content(
			model = self._model,
			contents = text
		)
		return resp.embeddings[0].values

	def embed_batch(self, texts: list[str]) -> list[list[float]]:
		out: list[list[float]] = []
		for i in range(0, len(texts), self._MAX_BATCH):
			chunk = texts[i: i + self._MAX_BATCH]
			resp = self._client.models.embed_content(
				model = self._model,
				content = chunk
			)
			out.extend(e.values for e in resp.embeddings)
		return out
