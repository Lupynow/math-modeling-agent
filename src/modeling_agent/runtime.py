from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .agent import ModelingAgent
from .config import Settings
from .knowledge import InMemoryKnowledgeStore, KnowledgeStore, QdrantKnowledgeStore
from .providers import (
    ChatProvider,
    EmbeddingProvider,
    FakeChatProvider,
    HashEmbeddingProvider,
    OpenAICompatibleChatProvider,
    OpenAICompatibleEmbeddingProvider,
)
from .repositories import InMemoryRepository, MySQLRepository, Repository
from .service import ModelingService


@dataclass
class Runtime:
    service: ModelingService | None
    repository: Repository | None
    knowledge_store: KnowledgeStore | None
    error: str | None = None


def resolve_knowledge_root(settings: Settings) -> Path:
    if settings.knowledge_root.exists():
        return settings.knowledge_root
    return (
        Path(__file__).resolve().parents[2]
        / "knowledge"
        / "math-modeling-skills"
        / "skills"
    )


def build_runtime(settings: Settings) -> Runtime:
    try:
        knowledge_root = resolve_knowledge_root(settings)
        if settings.app_mode == "fake":
            repository: Repository = InMemoryRepository()
            embedder: EmbeddingProvider = HashEmbeddingProvider()
            knowledge_store: KnowledgeStore = InMemoryKnowledgeStore(knowledge_root, embedder)
            chat_provider: ChatProvider = FakeChatProvider()
        else:
            if not settings.model_configured:
                raise RuntimeError("Production mode requires chat and embedding API configuration.")
            repository = MySQLRepository(settings.database_url)
            embedder = OpenAICompatibleEmbeddingProvider(
                base_url=settings.embedding_api_base,
                api_key=settings.embedding_api_key,
                model=settings.embedding_model,
                timeout_seconds=settings.request_timeout_seconds,
            )
            knowledge_store = QdrantKnowledgeStore(
                knowledge_root=knowledge_root,
                embedder=embedder,
                url=settings.qdrant_url,
                collection=settings.qdrant_collection,
            )
            chat_provider = OpenAICompatibleChatProvider(
                base_url=settings.chat_api_base,
                api_key=settings.chat_api_key,
                model=settings.chat_model,
                timeout_seconds=settings.request_timeout_seconds,
            )
            if not knowledge_store.ping():
                knowledge_store.reindex()

        agent = ModelingAgent(
            settings=settings,
            chat_provider=chat_provider,
            knowledge_store=knowledge_store,
        )
        service = ModelingService(settings=settings, repository=repository, agent=agent)
        return Runtime(
            service=service,
            repository=repository,
            knowledge_store=knowledge_store,
        )
    except Exception as exc:
        return Runtime(service=None, repository=None, knowledge_store=None, error=str(exc))
