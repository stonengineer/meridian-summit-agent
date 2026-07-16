"""
Generic hybrid retriever

Utilizes BM25 + Dense + RRF Logic but genericized over a `T: Searchable` rather
than hard-coded to a data type. It receives its searchable content via the
Searchable definition `searchable_text`, and returns `ScoredResult[T]` wrapper
that contains the original generic type as well as score values for that item.

This also features a generic (injected) embedding function, so this code has no
direct dependency on Vertex, OpenAI, or the offline has fallback.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Generic, Optional, TypeVar, Protocol

from .searchable import Searchable

T = TypeVar("T", bound=Searchable)

class Embedder(Protocol):
	def __call__(self, text: str) -> list[float]:
		# embed a single text (query time) #
		...
	def embed_batch(self, texts: list[str]) -> list[list[float]]:
		# embed batch of texts (index time) #
		...

_TOKEN_RE = re.compile(r"[a-z0-9]+")

def _tokenize(text: str) -> list[str]:
	return _TOKEN_RE.findall(text.lower())

@dataclass
class ScoredResult(Generic[T]):
	item: T
	hybrid_score: float
	sparse_score: Optional[int] = None
	dense_score: Optional[int] = None

# Hybrid Retriever
class HybridRetriever(Generic[T]):
	def __init__(self, items: list[T], embed: Embedder, *, top_k: int = 6):
		self.items = items
		self.embed = embed
		self.top_k = top_k

		# Index once during construction
		corpus_texts = [it.searchable_text for it in items]
		self._bm25 = _BM25(corpus_texts)
		self._dense = _Dense(corpus_texts, embed)

	def retrieve(
		self,
		query: str,
		top_k: Optional[int] = None
	) -> list[ScoredResult[T]]:
		k = top_k or self.top_k
		pool = max(k * 2, 8)

		sparse = self._bm25.search(query, pool)
		dense = self._dense.search(query, self.embed, pool)

		sparse_ranks = {
			idx: r
			for r, (idx, _) in enumerate(sparse)
		}
		dense_ranks = {
			idx: r
			for r, (idx, _) in enumerate(dense)
		}

		hybrid_ranks = self._rrf(sparse_ranks, dense_ranks)
		ranked_scores = sorted(
			hybrid_ranks.items(),
			key=lambda x: x[1],
			reverse=True
		)[:k]

		return [
			ScoredResult(
				item = self.items[idx],
				hybrid_score = score,
				sparse_score = sparse_ranks.get(idx),
				dense_score = dense_ranks.get(idx)
			)
			for idx, score in ranked_scores
		]

	@staticmethod
	def _rrf(
		sparse_ranks: dict[int,int],
		dense_ranks: dict[int,int],
		k: int = 60
	) -> dict[int,float]:
		# reciprocal rank fusion, each list contributes 1/(k+rank)
		hybrid_ranks: dict[int,float] = {}
		for idx, r in sparse_ranks.items():
			hybrid_ranks[idx] = hybrid_ranks.get(idx, 0.0) + 1.0 / (k + r)
		for idx, r in dense_ranks.items():
			hybrid_ranks[idx] = hybrid_ranks.get(idx, 0.0) + 1.0 / (k + r)
		return hybrid_ranks

# Sparse Retriever
class _BM25:
	def __init__(self, corpus_texts: list[str], k1: float = 1.5, b: float = 0.75):
		self.k1, self.b = k1, b
		self.docs = [_tokenize(t) for t in corpus_texts]
		self.doc_len = [len(d) for d in self.docs]
		self.n = len(self.docs)
		self.avgdl = (sum(self.doc_len) / self.n) if self.n else 0.0

		# build idf
		df: dict[str,int] = {}
		for doc in self.docs:
			for term in set(doc):
				df[term] = df.get(term, 0) + 1
		self.idf = {
			term: math.log(1 + (self.n - freq + 0.5) / (freq + 0.5))
			for term, freq in df.items()
		}

	def search(self, query: str, top_k: int) -> list[tuple[int,float]]:
		q_terms = _tokenize(query)
		scored: list[tuple[int,float]] = []
		for i, doc in enumerate(self.docs):
			if not doc:
				continue
			tf: dict[str,int] = {}
			for t in doc:
				tf[t] = tf.get(t, 0) + 1
			dl = self.doc_len[i]
			s: float = 0.0
			for t in q_terms:
				if t not in tf:
					continue
				num = tf[t] * (self.k1 + 1)
				norm_dl = 1 - self.b + self.b * dl / (self.avgdl or 1)
				den = tf[t] + self.k1 * norm_dl
				s += self.idf.get(t, 0.0) * num / den
			if s > 0:
				scored.append((i, s))
		scored.sort(key = lambda x: x[1], reverse=True)
		return scored[:top_k]

# Dense Retriever
class _Dense:
	def __init__(self, corpus_texts: list[str], embed: Embedder):
		self.vectors = [
			_l2_normalize(embed(t))
			for t in corpus_texts]

	def search(
		self,
		query: str,
		embed: Embedder,
		top_k: int
	) -> list[tuple[int,float]]:
		q = _l2_normalize(embed(query))
		sims = [(_dot(q, v)) for v in self.vectors]
		ranked = sorted(
			enumerate(sims),
			key=lambda x: x[1],
			reverse=True
		)
		return ranked[:top_k]

def _l2_normalize(v: list[float]) -> list[float]:
	norm = math.sqrt(sum(x * x for x in v)) or 1.0
	return [x / norm for x in v]

def _dot(a: list[float], b: list[float]) -> float:
	return sum(x * y for x, y in zip(a, b))