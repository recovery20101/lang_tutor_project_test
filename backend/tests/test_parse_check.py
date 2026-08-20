import pytest
import textwrap
from pathlib import Path
from pydantic import ValidationError

from app.scripts.parse_check import ChunkMetadata, Chunk, parse_chunks, parse_all, validate_all_links


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_meta(**overrides) -> dict:
    """Минимально валидный словарь метаданных с возможностью перезаписи полей."""
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
    meta = ChunkMetadata(**make_meta(id=chunk_id, related_nodes=related or []))
    return Chunk(text="Some rule text.", metadata=meta, source_file="test.md")


def write_md(tmp_path: Path, content: str) -> Path:
    """Записывает строку в temp-файл и возвращает путь."""
    p = tmp_path / "test.md"
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# ChunkMetadata — валидные случаи
# ---------------------------------------------------------------------------

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

    def test_summary_for_retrieval_optional(self):
        meta = ChunkMetadata(**make_meta(summary_for_retrieval="A summary."))
        assert meta.summary_for_retrieval == "A summary."

    def test_id_with_hyphens_and_dots(self):
        meta = ChunkMetadata(**make_meta(id="esp-gram-10.1.2.3"))
        assert meta.id == "esp-gram-10.1.2.3"


# ---------------------------------------------------------------------------
# ChunkMetadata — невалидные случаи
# ---------------------------------------------------------------------------

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

    def test_missing_required_field_raises(self):
        data = make_meta()
        del data["topic"]
        with pytest.raises(ValidationError):
            ChunkMetadata(**data)

    def test_level_lowercase_raises(self):
        with pytest.raises(ValidationError):
            ChunkMetadata(**make_meta(level="a1"))


# ---------------------------------------------------------------------------
# validate_all_links
# ---------------------------------------------------------------------------

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
        assert "c1" in broken[0]

    def test_multiple_broken_links(self):
        c1 = make_chunk("c1", related=["x", "y"])
        broken = validate_all_links([c1])
        assert len(broken) == 2

    def test_self_reference_valid(self):
        # Чанк ссылается сам на себя — технически нет битой ссылки
        c1 = make_chunk("c1", related=["c1"])
        assert validate_all_links([c1]) == []

    def test_empty_chunks_list(self):
        assert validate_all_links([]) == []

    def test_broken_link_message_format(self):
        c1 = make_chunk("esp-gram-10", related=["esp-gram-99"])
        broken = validate_all_links([c1])
        assert broken[0] == "[esp-gram-10] → 'esp-gram-99' not found"


# ---------------------------------------------------------------------------
# parse_chunks — файловые тесты
# ---------------------------------------------------------------------------

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

TWO_CHUNKS_MD = textwrap.dedent("""\
    First chunk text.

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

    Second chunk text.

    <!-- meta
    id: "esp-gram-1.2"
    source: "Spanish Essential Grammar"
    source_chapter: "1"
    source_section: "1.2"
    topic: "verb_forms"
    subtopic: "present_indicative"
    level: "A2"
    chunk_type: "formation"
    use_case: []
    flags: []
    related_nodes: ["esp-gram-1.1"]
    -->
""")

INVALID_LEVEL_MD = textwrap.dedent("""\
    Some text.

    <!-- meta
    id: "bad-chunk"
    source: "s"
    source_chapter: "1"
    source_section: "1"
    topic: "t"
    subtopic: "s"
    level: "C1"
    chunk_type: "rule"
    use_case: []
    flags: []
    related_nodes: []
    -->
""")

NO_META_MD = "# Just a heading\n\nSome content without any meta block."

EMPTY_TEXT_BEFORE_META_MD = textwrap.dedent("""\
    <!-- meta
    id: "esp-gram-1.1"
    source: "s"
    source_chapter: "1"
    source_section: "1"
    topic: "t"
    subtopic: "s"
    level: "A1"
    chunk_type: "rule"
    use_case: []
    flags: []
    related_nodes: []
    -->
    Some text after.
""")


class TestParseChunks:
    def test_parses_single_valid_chunk(self, tmp_path):
        p = write_md(tmp_path, VALID_MD)
        chunks = parse_chunks(p)
        assert len(chunks) == 1
        assert chunks[0].metadata.id == "esp-gram-1.1"
        assert chunks[0].source_file == "test.md"

    def test_chunk_text_is_captured(self, tmp_path):
        p = write_md(tmp_path, VALID_MD)
        chunks = parse_chunks(p)
        assert "Some rule text here" in chunks[0].text

    def test_parses_two_chunks(self, tmp_path):
        p = write_md(tmp_path, TWO_CHUNKS_MD)
        chunks = parse_chunks(p)
        assert len(chunks) == 2
        assert chunks[0].metadata.id == "esp-gram-1.1"
        assert chunks[1].metadata.id == "esp-gram-1.2"

    def test_skips_chunk_with_invalid_level(self, tmp_path):
        p = write_md(tmp_path, INVALID_LEVEL_MD)
        chunks = parse_chunks(p)
        assert chunks == []

    def test_returns_empty_for_no_meta_blocks(self, tmp_path):
        p = write_md(tmp_path, NO_META_MD)
        chunks = parse_chunks(p)
        assert chunks == []

    def test_skips_meta_with_empty_preceding_text(self, tmp_path):
        # Первый мета-блок не имеет текста перед собой — должен быть пропущен
        p = write_md(tmp_path, EMPTY_TEXT_BEFORE_META_MD)
        chunks = parse_chunks(p)
        assert len(chunks) == 0

    def test_related_nodes_parsed_correctly(self, tmp_path):
        p = write_md(tmp_path, TWO_CHUNKS_MD)
        chunks = parse_chunks(p)
        assert "esp-gram-1.1" in chunks[1].metadata.related_nodes

    def test_accepts_path_as_string(self, tmp_path):
        p = write_md(tmp_path, VALID_MD)
        chunks = parse_chunks(str(p))
        assert len(chunks) == 1

    def test_bad_yaml_skipped(self, tmp_path):
        bad_yaml_md = textwrap.dedent("""\
            Some text.

            <!-- meta
            id: [unclosed bracket
            -->
        """)
        p = write_md(tmp_path, bad_yaml_md)
        chunks = parse_chunks(p)
        assert chunks == []


# ---------------------------------------------------------------------------
# parse_all
# ---------------------------------------------------------------------------

class TestParseAll:
    def test_parses_multiple_files(self, tmp_path):
        (tmp_path / "a.md").write_text(VALID_MD, encoding="utf-8")
        second = VALID_MD.replace('esp-gram-1.1"', 'esp-gram-2.1"')
        (tmp_path / "b.md").write_text(second, encoding="utf-8")

        chunks = parse_all(tmp_path)
        assert len(chunks) == 2

    def test_empty_directory_returns_empty(self, tmp_path):
        chunks = parse_all(tmp_path)
        assert chunks == []

    def test_ignores_non_md_files(self, tmp_path):
        (tmp_path / "notes.txt").write_text("not markdown", encoding="utf-8")
        chunks = parse_all(tmp_path)
        assert chunks == []

    def test_files_processed_sorted(self, tmp_path):
        """parse_all обрабатывает файлы в алфавитном порядке."""
        (tmp_path / "z.md").write_text(VALID_MD, encoding="utf-8")
        second = VALID_MD.replace('esp-gram-1.1"', 'esp-gram-2.1"')
        (tmp_path / "a.md").write_text(second, encoding="utf-8")

        chunks = parse_all(tmp_path)
        # Файл a.md должен быть обработан первым
        assert chunks[0].metadata.id == "esp-gram-2.1"
        assert chunks[1].metadata.id == "esp-gram-1.1"
