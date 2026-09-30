"""Document parsing, chunking, embedding, and ownership-scoped retrieval."""

from __future__ import annotations

import io
import math
from dataclasses import dataclass
from heapq import nlargest
from pathlib import Path
from typing import Any

import anyio
from pypdf import PdfReader

from app.core.errors import ValidationError
from app.db.models import Document, DocumentChunk
from app.db.repositories import KnowledgeRepository
from app.providers.embedding import EmbeddingProvider

_PARSE_LIMITER = anyio.CapacityLimiter(2)


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    content: str
    score: float
    citation: dict[str, str]


class KnowledgeService:
    def __init__(
        self,
        repository: KnowledgeRepository,
        embeddings: EmbeddingProvider,
        *,
        chunk_chars: int,
        overlap_chars: int,
    ) -> None:
        self._repository = repository
        self._embeddings = embeddings
        self._chunk_chars = chunk_chars
        self._overlap_chars = overlap_chars

    async def ingest(
        self, *, user_id: str, filename: str, content_type: str | None, data: bytes, metadata: dict[str, Any]
    ) -> Document:
        if not isinstance(metadata, dict):
            raise ValidationError("Metadata must be a JSON object")
        filename = Path(filename.replace("\\", "/")).name
        if len(filename) > 240:
            raise ValidationError("Filename is too long")
        try:
            content = await anyio.to_thread.run_sync(
                _parse_document, filename, content_type, data, limiter=_PARSE_LIMITER
            )
        except Exception as exc:
            raise ValidationError("Document cannot be parsed; upload UTF-8 text or a valid PDF") from exc
        if len(content) > 1_000_000:
            raise ValidationError("Extracted document text is too large")
        pieces = _chunk(content, self._chunk_chars, self._overlap_chars)
        if len(pieces) > 2_000:
            raise ValidationError("Document produces too many chunks")
        vectors: list[list[float]] = []
        for offset in range(0, len(pieces), 64):
            vectors.extend(await self._embeddings.embed(pieces[offset : offset + 64]))
        document = Document(
            user_id=user_id, title=Path(filename).stem, source=filename, metadata_json=metadata, content=content
        )
        chunks = [
            DocumentChunk(chunk_index=index, content=piece, embedding=vector)
            for index, (piece, vector) in enumerate(zip(pieces, vectors, strict=True))
        ]
        async with self._repository.session.begin():
            return await self._repository.create(document, chunks)

    async def search(self, user_id: str, query: str, top_k: int) -> list[RetrievedChunk]:
        query_vector = (await self._embeddings.embed([query]))[0]
        database_results = await self._repository.search_similar(user_id, query_vector, top_k)
        if database_results is not None:
            return [
                RetrievedChunk(
                    content=chunk.content,
                    score=score,
                    citation={"documentId": document.id, "chunkId": chunk.id, "title": document.title},
                )
                for chunk, document, score in database_results
            ]
        candidates = await self._repository.chunks(user_id)
        scored = (
            RetrievedChunk(
                content=chunk.content,
                score=_cosine(query_vector, list(chunk.embedding)),
                citation={"documentId": document.id, "chunkId": chunk.id, "title": document.title},
            )
            for chunk, document in candidates
        )
        # SQLite's fallback scores every candidate, but need only retain the
        # best matches instead of materializing and sorting all result objects.
        return nlargest(top_k, scored, key=lambda item: item.score)


def _parse_document(filename: str, content_type: str | None, data: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in {".txt", ".md"}:
        return data.decode("utf-8")
    if (
        suffix == ".pdf"
        and data.startswith(b"%PDF-")
        and content_type in {"application/pdf", "application/octet-stream", None}
    ):
        reader = PdfReader(io.BytesIO(data))
        if len(reader.pages) > 200:
            raise ValueError("PDF has too many pages")
        parts: list[str] = []
        extracted = 0
        for page in reader.pages:
            text = page.extract_text() or ""
            extracted += len(text)
            if extracted > 1_000_000:
                raise ValueError("PDF text is too large")
            parts.append(text)
        return "\n".join(parts)
    raise ValueError("Only .txt, .md and .pdf documents are supported")


def _chunk(content: str, size: int, overlap: int) -> list[str]:
    normalized = content.strip()
    if not normalized:
        raise ValueError("Document contains no extractable text")
    step = size - overlap
    return [normalized[index : index + size] for index in range(0, len(normalized), step)]


def _cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    denominator = math.sqrt(sum(a * a for a in left)) * math.sqrt(sum(b * b for b in right))
    return numerator / denominator if denominator else 0.0
