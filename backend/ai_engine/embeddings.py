import hashlib
import logging
import math
import re
from typing import Literal

import httpx

from core.config import settings

logger = logging.getLogger(__name__)


_STOP_WORDS = {
    "a", "about", "above", "after", "again", "all", "an", "and", "any", "are", "as",
    "at", "be", "because", "been", "before", "below", "between", "both", "but",
    "by", "do", "does", "during", "each", "for", "from", "further", "has", "have",
    "how", "i", "if", "in", "into", "is", "it", "its", "more", "most", "no", "nor",
    "not", "of", "off", "on", "once", "only", "or", "other", "our", "out", "over",
    "so", "some", "such", "than", "that", "the", "their", "then", "there", "these",
    "they", "this", "those", "through", "to", "too", "under", "until", "up", "very",
    "was", "we", "were", "what", "when", "where", "which", "while", "who", "whom",
    "why", "with", "would", "you", "your"
}


class EmbeddingService:
    """
    Dịch vụ trích xuất vector embedding đa tầng (Multi-tier Embedding Service):
    1. OpenAI Embeddings API (text-embedding-3-small, 1536 dims) nếu có OPENAI_API_KEY.
    2. Google Gemini Embedding API nếu có GEMINI_API_KEY.
    3. Deterministic Semantic Feature Vectorizer (Local Fallback):
       Sử dụng Feature Hashing n-gram (unigrams + bigrams) với multi-seed random projection
       và chuẩn hóa L2 norm 1536 chiều. Đảm bảo 100% không phụ thuộc internet/API key
       và phản ánh chính xác khoảng cách cosine trong pgvector.
    """

    def __init__(
        self,
        dimension: int = 1536,
        provider: Literal["auto", "openai", "gemini", "local"] = "auto",
    ):
        self.dimension = dimension
        self.provider = provider

    def _determine_active_provider(self) -> str:
        if self.provider != "auto":
            return self.provider
        if settings.openai_api_key:
            return "openai"
        if settings.gemini_api_key:
            return "gemini"
        return "local"

    def compute_local_embedding(self, text: str) -> list[float]:
        """
        Tạo vector 1536 chiều bằng Feature Hashing n-gram.
        Cho phép tìm kiếm độ tương đồng Cosine chuẩn xác mà không cần API bên ngoài.
        """
        all_words = re.findall(r"\b\w+\b", text.lower())
        if not all_words:
            return [0.0] * self.dimension

        # Lọc bỏ stop words để tập trung vào các từ mang ngữ nghĩa chính
        words = [w for w in all_words if w not in _STOP_WORDS]
        if not words:
            words = all_words

        vec = [0.0] * self.dimension
        tokens = list(words)
        # Bổ sung 2-grams để nắm bắt các cụm thuật ngữ (ví dụ: 'order_block', 'fair_value_gap')
        for i in range(len(words) - 1):
            tokens.append(f"{words[i]}_{words[i+1]}")

        for token in tokens:
            for seed in (0, 1, 2):
                h = int(hashlib.sha256(f"{seed}:{token}".encode("utf-8")).hexdigest(), 16)
                idx = h % self.dimension
                sign = 1.0 if (h >> 16) % 2 == 0 else -1.0
                vec[idx] += sign

        # Chuẩn hóa L2-norm để độ dài vector = 1.0 (chuẩn cho Cosine Distance)
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0.0:
            vec = [round(x / norm, 6) for x in vec]
        return vec

    async def _embed_openai(self, texts: list[str]) -> list[list[float]]:
        url = "https://api.openai.com/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "input": texts,
            "model": settings.embedding_model or "text-embedding-3-small",
            "dimensions": self.dimension,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return [item["embedding"] for item in data["data"]]

    async def _embed_gemini(self, text: str) -> list[float]:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent"
            f"?key={settings.gemini_api_key}"
        )
        payload = {
            "model": "models/text-embedding-004",
            "content": {"parts": [{"text": text}]},
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            raw_vec = resp.json()["embedding"]["values"]
            # Pad hoặc project nếu chiều khác 1536 (Gemini thường 768)
            if len(raw_vec) == self.dimension:
                return raw_vec
            if len(raw_vec) < self.dimension:
                raw_vec = raw_vec + [0.0] * (self.dimension - len(raw_vec))
            else:
                raw_vec = raw_vec[: self.dimension]
            norm = math.sqrt(sum(x * x for x in raw_vec))
            return [x / norm for x in raw_vec] if norm > 0 else raw_vec

    async def embed_text(self, text: str) -> list[float]:
        """Tạo vector embedding cho một chuỗi văn bản đơn lẻ"""
        active_provider = self._determine_active_provider()
        if active_provider == "openai":
            try:
                embeddings = await self._embed_openai([text])
                return embeddings[0]
            except Exception as exc:
                logger.warning("OpenAI embedding failed (%s), falling back to local vectorizer", exc)
                return self.compute_local_embedding(text)

        if active_provider == "gemini":
            try:
                return await self._embed_gemini(text)
            except Exception as exc:
                logger.warning("Gemini embedding failed (%s), falling back to local vectorizer", exc)
                return self.compute_local_embedding(text)

        return self.compute_local_embedding(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Tạo vector embeddings cho một danh sách văn bản theo lô"""
        if not texts:
            return []
        active_provider = self._determine_active_provider()
        if active_provider == "openai":
            try:
                return await self._embed_openai(texts)
            except Exception as exc:
                logger.warning("OpenAI batch embedding failed (%s), falling back to local vectorizer", exc)
                return [self.compute_local_embedding(t) for t in texts]

        return [self.compute_local_embedding(t) for t in texts]


embedding_service = EmbeddingService()
