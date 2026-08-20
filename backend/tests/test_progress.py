from pathlib import Path
import textwrap
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta, timezone
import pytest
from pydantic import ValidationError

from app.routers.progress import get_user_progress_dashboard, parse_chunk_id_for_sort
from app.schemas.progress import ProgressDashboardResponse
from app.scripts.parse_check import Chunk, ChunkMetadata, parse_all, parse_chunks, validate_all_links
from app.services.sm2 import calculate_sm2


# ===========================================================================
# Helpers for test_parse_check
# ===========================================================================

def make_meta(**overrides) -> dict:
    """Returns a minimally valid metadata dictionary with optional overrides."""
    base = {
        "id": "esp-gram-1.1",
        "source": "Spanish Essential Grammar",
        "source_chapter": "1",
        "source_section": "1.1",
        "topic": "verb_forms",
        "subtopic": "present_indicative",
        "level": "A1",
        "chunk_type": "rule",
    }
    base.update(overrides)
    return base


def make_chunk(chunk_id: str = "esp-gram-1.1", related: list[str] | None = None) -> Chunk:
    """Returns a mock Chunk instance for testing links."""
    meta = ChunkMetadata(**make_meta(id=chunk_id, related_nodes=related or []))
    return Chunk(text="Some rule text.", metadata=meta, source_file="test.md")


def write_md(tmp_path: Path, content: str) -> Path:
    """Writes content to a temporary markdown file and returns its path."""
    p = tmp_path / "test.md"
    p.write_text(content, encoding="utf-8")
    return p


# ===========================================================================
# Test Suite: test_parse_check.py
# ===========================================================================

class TestChunkMetadataValid:
    def test_minimal_required_fields(self):
        meta = ChunkMetadata(**make_meta())
        assert meta.id == "esp-gram-1.1"
        assert meta.level == "A1"
        assert meta.chunk_type == "rule"

    def test_all_valid_levels(self):
        for level in ("A1", "A2", "B1", "B2"):
            meta = ChunkMetadata(**make_meta(level=level))
            assert meta.level == level

    def test_all_valid_chunk_types(self):
        for ct in ("rule", "formation", "comparison", "usage_note", "reference", "intro"):
            meta = ChunkMetadata(**make_meta(chunk_type=ct))
            assert meta.chunk_type == ct

    def test_optional_tense_defaults_to_none(self):
        meta = ChunkMetadata(**make_meta())
        assert meta.tense is None

    def test_tense_set(self):
        meta = ChunkMetadata(**make_meta(tense="present"))
        assert meta.tense == "present"

    def test_lists_default_to_empty(self):
        meta = ChunkMetadata(**make_meta())
        assert meta.use_case == []
        assert meta.flags == []
        assert meta.related_nodes == []

    def test_lists_populated(self):
        meta = ChunkMetadata(**make_meta(
            use_case=["narrative"],
            flags=["common_mistake"],
            related_nodes=["esp-gram-2.1"]
        ))
        assert "narrative" in meta.use_case
        assert "common_mistake" in meta.flags
        assert "esp-gram-2.1" in meta.related_nodes


class TestChunkMetadataInvalid:
    def test_empty_id_raises(self):
        with pytest.raises(ValidationError):
            ChunkMetadata(**make_meta(id=""))

    def test_whitespace_only_id_raises(self):
        with pytest.raises(ValidationError):
            ChunkMetadata(**make_meta(id="   "))

    def test_invalid_level_raises(self):
        with pytest.raises(ValidationError):
            ChunkMetadata(**make_meta(level="C1"))

    def test_invalid_chunk_type_raises(self):
        with pytest.raises(ValidationError):
            ChunkMetadata(**make_meta(chunk_type="unknown_type"))


class TestValidateAllLinks:
    def test_no_links_returns_empty(self):
        chunks = [make_chunk("c1"), make_chunk("c2")]
        assert validate_all_links(chunks) == []

    def test_valid_link_returns_empty(self):
        c1 = make_chunk("c1", related=["c2"])
        c2 = make_chunk("c2")
        assert validate_all_links([c1, c2]) == []

    def test_broken_link_detected(self):
        c1 = make_chunk("c1", related=["missing"])
        broken = validate_all_links([c1])
        assert len(broken) == 1
        assert "missing" in broken[0]


VALID_MD = textwrap.dedent("""\
    # Section title

    Some rule text here.

    <!-- meta
    id: "esp-gram-1.1"
    source: "Spanish Essential Grammar"
    source_chapter: "1"
    source_section: "1.1"
    topic: "verb_forms"
    subtopic: "present_indicative"
    level: "A1"
    chunk_type: "rule"
    use_case: []
    flags: []
    related_nodes: []
    -->
""")


class TestParseChunks:
    def test_parses_single_valid_chunk(self, tmp_path):
        p = write_md(tmp_path, VALID_MD)
        chunks = parse_chunks(p)
        assert len(chunks) == 1
        assert chunks[0].metadata.id == "esp-gram-1.1"


class TestParseAll:
    def test_empty_directory_returns_empty(self, tmp_path):
        chunks = parse_all(tmp_path)
        assert chunks == []


# ===========================================================================
# Test Suite: test_progress.py
# ===========================================================================

def test_parse_chunk_id_for_sort():
    assert parse_chunk_id_for_sort("abc-1-2") == [1, 2]
    assert parse_chunk_id_for_sort("rules-10") == [10]
    assert parse_chunk_id_for_sort("no-numbers") == []


@pytest.mark.asyncio
async def test_get_user_progress_dashboard_success():
    mock_user = MagicMock()
    mock_user.id = 42
    mock_user.current_level = "A1"

    mock_total_rules_result = MagicMock()
    mock_total_rules_result.all.return_value = [
        ("Grammar", 10),
        ("Vocabulary", 5)
    ]

    mock_completed_rules_result = MagicMock()
    mock_completed_rules_result.all.return_value = [
        ("Grammar", 4),
    ]

    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    mock_reviews_result = MagicMock()
    mock_reviews_result.all.return_value = [
        ("esp-gram-1.1", now_utc - timedelta(days=3), "Presente Ser"),
        ("esp-gram-1.2", now_utc - timedelta(days=1), "Presente Estar"),
    ]

    mock_db = AsyncMock()
    mock_db.execute.side_effect = [
        mock_total_rules_result,
        mock_completed_rules_result,
        mock_reviews_result
    ]

    response = await get_user_progress_dashboard(
        lang="es",
        current_user=mock_user,
        db=mock_db
    )

    assert isinstance(response, ProgressDashboardResponse)
    assert len(response.topics) == 2


# ===========================================================================
# Test Suite: test_rag.py
# ===========================================================================

def make_collection_get_result(ids=None, documents=None, metadatas=None):
    return {
        "ids": ids or [],
        "documents": documents or [],
        "metadatas": metadatas or [],
    }


def make_collection_query_result(ids=None, documents=None, metadatas=None):
    return {
        "ids": [ids or []],
        "documents": [documents or []],
        "metadatas": [metadatas or []],
    }


def make_mock_model():
    model = MagicMock()
    model.encode.return_value = MagicMock(tolist=lambda: [0.0] * 384)
    return model


@pytest.fixture
def get_context():
    from app.services.rag import get_extended_context
    return get_extended_context


@pytest.mark.asyncio
async def test_a1_user_only_gets_a1(get_context):
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


# ===========================================================================
# Test Suite: test_sm2.py
# ===========================================================================

def test_calculate_sm2_perfect_response():
    result = calculate_sm2(score_10=10, repetitions=0, interval=0, easiness_factor=2.5)
    assert result["repetitions"] == 1
    assert result["interval"] == 1
    assert result["easiness_factor"] == 2.60
    assert result["status"] == "mastered"


def test_calculate_sm2_bad_response():
    result = calculate_sm2(score_10=1, repetitions=5, interval=10, easiness_factor=2.5)
    assert result["repetitions"] == 0
    assert result["interval"] == 1
    assert result["status"] == "learning"
    assert result["easiness_factor"] == 1.7
