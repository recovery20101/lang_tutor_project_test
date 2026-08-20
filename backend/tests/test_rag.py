"""
Tests for app/services/rag.py — get_extended_context()
All external dependencies (ChromaDB, embeddings) are mocked.
"""

import pytest
from unittest.mock import MagicMock


def make_collection_get_result(ids=None, documents=None, metadatas=None):
    """Mocks collection.get() response."""
    return {
        "ids": ids or [],
        "documents": documents or [],
        "metadatas": metadatas or [],
    }


def make_collection_query_result(ids=None, documents=None, metadatas=None):
    """Mocks collection.query() response."""
    return {
        "ids": [ids or []],
        "documents": [documents or []],
        "metadatas": [metadatas or []],
    }


def make_mock_model():
    """Mock embedding model returning a zero vector."""
    model = MagicMock()
    model.encode.return_value = MagicMock(tolist=lambda: [0.0] * 384)
    return model


@pytest.fixture
def get_context():
    from app.services.rag import get_extended_context
    return get_extended_context


@pytest.mark.asyncio
class TestAllowedLevels:
    """Verifies that level-based filtering functions correctly."""

    async def test_a1_user_only_gets_a1(self, get_context):
        collection = MagicMock()
        collection.get.return_value = make_collection_get_result()
        collection.query.return_value = make_collection_query_result(
            ids=["esp-gram-1", "esp-gram-2"],
            documents=["doc1", "doc2"],
            metadatas=[{"level": "A2", "related_nodes": ""}, {"level": "A1", "related_nodes": ""}],
        )

        result = await get_context("present tense", collection, make_mock_model(), user_level="A1")

        assert "esp-gram-2" in result["ids"][0]
        assert "esp-gram-1" not in result["ids"][0]

    async def test_b2_user_gets_all_levels(self, get_context):
        collection = MagicMock()
        collection.get.return_value = make_collection_get_result()
        collection.query.return_value = make_collection_query_result(
            ids=["c1", "c2", "c3", "c4"],
            documents=["d1", "d2", "d3", "d4"],
            metadatas=[
                {"level": "A1", "related_nodes": ""},
                {"level": "A2", "related_nodes": ""},
                {"level": "B1", "related_nodes": ""},
                {"level": "B2", "related_nodes": ""},
            ],
        )

        result = await get_context("subjunctive", collection, make_mock_model(), user_level="B2")
        assert len(result["ids"][0]) == 4


@pytest.mark.asyncio
class TestDirectChunkIdLookup:
    """Tests direct chunk ID lookup when query contains chunk pattern."""

    async def test_direct_lookup_triggered_by_chunk_id_in_query(self, get_context):
        collection = MagicMock()
        collection.get.side_effect = [
            make_collection_get_result(
                ids=["esp-gram-10.1"],
                documents=["Present indicative text"],
                metadatas=[{"level": "A1", "related_nodes": ""}],
            ),
        ]
        collection.query.return_value = make_collection_query_result()

        result = await get_context("esp-gram-10.1", collection, make_mock_model(), user_level="A1")

        collection.get.assert_called()
        assert "esp-gram-10.1" in result["ids"][0]


@pytest.mark.asyncio
class TestSemanticSearch:
    """Tests semantic search invocation and filtering."""

    async def test_semantic_search_always_called(self, get_context):
        collection = MagicMock()
        collection.get.return_value = make_collection_get_result()
        collection.query.return_value = make_collection_query_result()

        await get_context("how to conjugate verbs", collection, make_mock_model(), user_level="A1")
        collection.query.assert_called_once()
