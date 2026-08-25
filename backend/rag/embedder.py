"""
rag/embedder.py — Embedding service wrapper with deterministic fallback.
Primary: text-embedding-004 (768-dim)
Fallback: Deterministic hash-based 768-dim vectors for testing/offline environments.
"""
import hashlib
import logging
import math
from typing import Optional
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Embedding generation service.
    Primary: Google text-embedding-004 (768-dim)
    Offline / Test fallback: Deterministic 768-dim unit vectors.
    """

    EMBEDDING_DIM = 768
    CACHE_TTL = 86400  # 24 hours
    CACHE_PREFIX = "embed:"

    def __init__(self, model: Optional[str] = None):
        self.model = model or getattr(settings, "LLM_EMBEDDING_MODEL", "models/text-embedding-004")
        self._client = None
        self._api_key = getattr(settings, "GOOGLE_API_KEY", "")

    def _get_client(self):
        if self._client is None and self._api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self._api_key)
                self._client = genai
            except Exception as e:
                logger.warning("Could not initialize Google GenAI client: %s", e)
                self._client = False
        return self._client

    def embed_single(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
        """
        Embed a single text string. Returns a 768-dimensional float list.
        """
        text = self._preprocess(text)
        cache_key = f"{self.CACHE_PREFIX}{hashlib.md5(text.encode('utf-8')).hexdigest()}"

        cached = cache.get(cache_key)
        if cached:
            return cached

        client = self._get_client()
        if client and self._api_key and self._api_key != "mock-google-api-key":
            try:
                result = client.embed_content(
                    model=self.model,
                    content=text,
                    task_type=task_type,
                )
                embedding = result["embedding"]
                cache.set(cache_key, embedding, timeout=self.CACHE_TTL)
                return embedding
            except Exception as e:
                logger.warning("Live embedding call failed, falling back to local deterministic vector: %s", e)

        # Deterministic offline vector generation
        embedding = self._generate_deterministic_vector(text)
        cache.set(cache_key, embedding, timeout=self.CACHE_TTL)
        return embedding

    def embed_batch(self, texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
        """Embed a batch of texts."""
        return [self.embed_single(t, task_type=task_type) for t in texts]

    def embed_query(self, query: str) -> list[float]:
        """Embed a user query for retrieval."""
        return self.embed_single(query, task_type="RETRIEVAL_QUERY")

    def _generate_deterministic_vector(self, text: str) -> list[float]:
        """
        Generate a normalized, deterministic 768-dimensional unit vector from text.
        Ensures consistent cosine similarity in offline testing.
        """
        vec = []
        # Generate 768 floats deterministically from iterative hashes
        for i in range(self.EMBEDDING_DIM // 16):
            seed = f"{text}_{i}".encode("utf-8")
            digest = hashlib.sha256(seed).digest()
            for b in digest[:16]:
                # Map byte 0..255 to -1.0 .. 1.0
                vec.append((b - 128) / 128.0)

        # Pad to exactly 768 if needed
        while len(vec) < self.EMBEDDING_DIM:
            vec.append(0.0)
        vec = vec[: self.EMBEDDING_DIM]

        # Normalize to unit length (L2 norm)
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    def _preprocess(self, text: str) -> str:
        """Clean and truncate text before embedding."""
        text = text.strip()
        text = " ".join(text.split())
        if len(text) > 8000:
            text = text[:8000]
        return text

    @property
    def dimension(self) -> int:
        return self.EMBEDDING_DIM
