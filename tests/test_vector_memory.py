"""
Unit Tests for VectorMemory

Tests Pinecone init paths, metadata handling, and query behavior.
"""

import sys
from pathlib import Path
from datetime import datetime

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from memory import vector_store


class FakeEmbeddingData:
    def __init__(self, embedding):
        self.embedding = embedding


class FakeEmbeddingResponse:
    def __init__(self, embedding):
        self.data = [FakeEmbeddingData(embedding)]


class FakeOpenAIEmbeddings:
    def __init__(self, embedding=None):
        self._embedding = embedding or [0.1, 0.2, 0.3]

    def create(self, model, input):
        return FakeEmbeddingResponse(self._embedding)


class FakeOpenAI:
    def __init__(self, *args, **kwargs):
        self.api_key = kwargs.get("api_key")
        self.embeddings = FakeOpenAIEmbeddings()


class FakeIndex:
    def __init__(self):
        self.upsert_calls = []
        self.query_calls = []
        self.vectors = []

    def upsert(self, vectors, namespace=None):
        self.upsert_calls.append((vectors, namespace))
        self.vectors.extend(vectors)

    def query(self, **kwargs):
        self.query_calls.append(kwargs)
        matches = []
        for vector_id, _, metadata in self.vectors:
            matches.append({"id": vector_id, "score": 0.9, "metadata": metadata})
        return {"matches": matches}


class FakePineconeModule:
    def __init__(self):
        self.init_called = False
        self.init_args = {}
        self.indexes = []
        self.created_indexes = []
        self.last_create = {}

    def init(self, api_key=None, environment=None):
        self.init_called = True
        self.init_args = {"api_key": api_key, "environment": environment}

    def list_indexes(self):
        return list(self.indexes)

    def create_index(self, name, dimension, metric):
        self.created_indexes.append(name)
        self.indexes.append(name)
        self.last_create = {"name": name, "dimension": dimension, "metric": metric}

    def Index(self, name):
        return FakeIndex()


@pytest.fixture
def env_keys(monkeypatch):
    monkeypatch.setenv("PINECONE_API_KEY", "test-key")
    monkeypatch.setenv("PINECONE_ENV", "us-east-1-aws")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")


def test_store_and_retrieve(monkeypatch, env_keys):
    fake_index = FakeIndex()
    monkeypatch.setattr(vector_store, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(
        vector_store.VectorMemory,
        "_init_pinecone_index",
        lambda self: fake_index
    )

    memory = vector_store.VectorMemory(dimension=3)
    metadata = {"key_insight": "Key insight", "extra": {"at": datetime(2024, 1, 1, 0, 0, 0)}}
    analysis_text = "A" * 2100

    vector_id = memory.store_analysis("NVDA", analysis_text, metadata)

    assert len(vector_id) == 32
    assert len(fake_index.upsert_calls) == 1
    vectors, namespace = fake_index.upsert_calls[0]
    assert namespace == "analyses"

    stored_id, stored_vector, stored_meta = vectors[0]
    assert stored_id == vector_id
    assert stored_meta["ticker"] == "NVDA"
    assert stored_meta["summary"] == "Key insight"
    assert stored_meta["analysis_text"].endswith("...")
    assert stored_meta["extra"]["at"] == "2024-01-01T00:00:00"

    results = memory.retrieve_similar_analyses("query text", top_k=2, ticker="NVDA")
    assert fake_index.query_calls[-1]["filter"] == {"ticker": {"$eq": "NVDA"}}
    assert len(results) == 1
    assert results[0]["metadata"]["ticker"] == "NVDA"

    memory.retrieve_similar_analyses("query text", top_k=2, ticker=None)
    assert "filter" not in fake_index.query_calls[-1]


def test_parse_environment(monkeypatch, env_keys):
    monkeypatch.setattr(vector_store, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(
        vector_store.VectorMemory,
        "_init_pinecone_index",
        lambda self: FakeIndex()
    )

    memory = vector_store.VectorMemory(dimension=3)
    assert memory._parse_environment("us-east-1-aws") == ("aws", "us-east-1")
    assert memory._parse_environment("us-east-1") == ("aws", "us-east-1")


def test_init_pinecone_index_creates(monkeypatch, env_keys):
    fake_pinecone = FakePineconeModule()
    monkeypatch.setattr(vector_store, "pinecone", fake_pinecone)
    monkeypatch.setattr(vector_store, "OpenAI", FakeOpenAI)

    memory = vector_store.VectorMemory(index_name="test-index", dimension=3)
    assert fake_pinecone.init_called is True
    assert fake_pinecone.created_indexes == ["test-index"]
    assert fake_pinecone.last_create["dimension"] == 3
    assert memory.index is not None
