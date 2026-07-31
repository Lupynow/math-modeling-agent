from __future__ import annotations

import hashlib
import math
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from .providers import EmbeddingProvider
from .schemas import EvidenceCitation


@dataclass(frozen=True)
class KnowledgeChunk:
    chunk_id: str
    source_path: str
    section: str
    text: str
    content_hash: str


def chunk_markdown(path: Path, root: Path) -> list[KnowledgeChunk]:
    text = path.read_text(encoding="utf-8")
    relative = path.relative_to(root).as_posix()
    chunks: list[KnowledgeChunk] = []
    heading = "Introduction"
    body: list[str] = []

    def flush() -> None:
        content = "\n".join(body).strip()
        if not content:
            return
        digest = hashlib.sha256(f"{relative}\n{heading}\n{content}".encode()).hexdigest()
        chunks.append(
            KnowledgeChunk(
                chunk_id=str(uuid5(NAMESPACE_URL, digest)),
                source_path=relative,
                section=heading,
                text=content[:4000],
                content_hash=digest,
            )
        )

    for line in text.splitlines():
        match = re.match(r"^#{1,4}\s+(.+)$", line)
        if match:
            flush()
            heading = match.group(1).strip()
            body = []
        else:
            body.append(line)
    flush()
    return chunks


def load_knowledge_chunks(knowledge_root: Path) -> list[KnowledgeChunk]:
    if not knowledge_root.exists():
        return []
    chunks: list[KnowledgeChunk] = []
    for path in sorted(knowledge_root.rglob("*.md")):
        if any(part in {"code-templates", "playbooks"} for part in path.parts):
            continue
        chunks.extend(chunk_markdown(path, knowledge_root))
    return chunks


class KnowledgeStore(ABC):
    @abstractmethod
    def reindex(self) -> int: ...

    @abstractmethod
    def search(self, query: str, limit: int = 8) -> list[EvidenceCitation]: ...

    @abstractmethod
    def ping(self) -> bool: ...


class InMemoryKnowledgeStore(KnowledgeStore):
    def __init__(self, knowledge_root: Path, embedder: EmbeddingProvider) -> None:
        self.knowledge_root = knowledge_root
        self.embedder = embedder
        self._chunks: list[KnowledgeChunk] = []
        self._vectors: list[list[float]] = []
        self.reindex()

    def reindex(self) -> int:
        self._chunks = load_knowledge_chunks(self.knowledge_root)
        self._vectors = self.embedder.embed([chunk.text for chunk in self._chunks])
        return len(self._chunks)

    def search(self, query: str, limit: int = 8) -> list[EvidenceCitation]:
        if not self._chunks:
            return []
        query_vector = self.embedder.embed([query])[0]
        scored = []
        for chunk, vector in zip(self._chunks, self._vectors, strict=True):
            score = sum(left * right for left, right in zip(query_vector, vector, strict=True))
            scored.append((score, chunk))
        citations = []
        for score, chunk in sorted(scored, reverse=True, key=lambda item: item[0])[:limit]:
            normalized_score = max(0.0, min(1.0, float(score)))
            citations.append(
                EvidenceCitation(
                    source_path=chunk.source_path,
                    section=chunk.section,
                    excerpt=" ".join(chunk.text.split())[:300],
                    score=normalized_score,
                )
            )
        return citations

    def ping(self) -> bool:
        return bool(self._chunks)


class QdrantKnowledgeStore(KnowledgeStore):
    def __init__(
        self,
        *,
        knowledge_root: Path,
        embedder: EmbeddingProvider,
        url: str,
        collection: str,
    ) -> None:
        from qdrant_client import QdrantClient

        self.knowledge_root = knowledge_root
        self.embedder = embedder
        self.collection = collection
        self.client = QdrantClient(url=url)

    def reindex(self) -> int:
        from qdrant_client.models import Distance, PointStruct, VectorParams

        chunks = load_knowledge_chunks(self.knowledge_root)
        if not chunks:
            return 0
        vectors = self.embedder.embed([chunk.text for chunk in chunks])
        dimension = len(vectors[0])
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
            )
        points = [
            PointStruct(
                id=chunk.chunk_id,
                vector=vector,
                payload={
                    "source_path": chunk.source_path,
                    "section": chunk.section,
                    "text": chunk.text,
                    "content_hash": chunk.content_hash,
                },
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        self.client.upsert(collection_name=self.collection, points=points, wait=True)
        return len(points)

    def search(self, query: str, limit: int = 8) -> list[EvidenceCitation]:
        vector = self.embedder.embed([query])[0]
        result = self.client.query_points(
            collection_name=self.collection,
            query=vector,
            limit=limit,
            with_payload=True,
        )
        citations: list[EvidenceCitation] = []
        for point in result.points:
            payload = point.payload or {}
            score = float(point.score or 0)
            if math.isnan(score):
                score = 0
            citations.append(
                EvidenceCitation(
                    source_path=str(payload.get("source_path", "")),
                    section=str(payload.get("section", "")),
                    excerpt=" ".join(str(payload.get("text", "")).split())[:300],
                    score=max(0.0, min(1.0, score)),
                )
            )
        return citations

    def ping(self) -> bool:
        try:
            return self.client.collection_exists(self.collection)
        except Exception:
            return False
