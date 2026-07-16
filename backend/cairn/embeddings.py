"""
Embedding Function definitions

Based on the environment variables, select the embedding function for the
hybrid retrievers to use
"""

import re
import os
import logging

from .retrieval.hybrid_retriever import Embedder
from .config import get_config, Config

LOGGER = logging.getLogger(__name__)
_TOKEN_RE = re.compile(r"[a-z0-9]+")

def get_embed_fn() -> Embedder:
	cfg: Config = get_config()
	if not cfg.use_vertex:
		return _HashEmbedder()
	model = _try_init_vertex(cfg)
	if model is None:
		LOGGER.warning(
			"[embeddings] Vertex requested but unavailable; using offline fallback")
		return _HashEmbedder()
	return _VertexEmbedder(model)

def _try_init_vertex(cfg: Config):
	try:
		import vertexai
		from vertexai.language_models import TextEmbeddingModel

		vertexai.init(
			project = cfg.gcp_project_id,
			location = cfg.gcp_region
		)
		return TextEmbeddingModel.from_pretrained(
			cfg.embedding_model
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

	def __init__(self, model):
		self._model = model

	def __call__(self, text: str) -> list[float]:
		return self._model.get_embeddings([text])[0].values

	def embed_batch(self, texts: list[str]) -> list[list[float]]:
		out: list[list[float]] = []
		for i in range(0, len(texts), self._MAX_BATCH):
			chunk = texts[i: i + self._MAX_BATCH]
			out.extend(e.values for e in self._model.get_embeddings(chunk))
		return out
