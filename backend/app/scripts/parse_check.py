from collections import Counter
from pathlib import Path
import re
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator
import yaml


class ChunkMetadata(BaseModel):
    """Schema for markdown chunk metadata parsed from YAML blocks."""

    id: str
    source: str
    source_chapter: str
    source_section: str
    topic: str
    subtopic: str
    tense: Optional[str] = None

    level: Literal["A1", "A2", "B1", "B2"]
    chunk_type: Literal["rule", "formation", "comparison", "usage_note", "reference", "intro"]

    use_case: List[str] = Field(default_factory=list)
    flags: List[str] = Field(default_factory=list)
    related_nodes: List[str] = Field(default_factory=list)
    summary_for_retrieval: Optional[str] = None

    @field_validator('id')
    @classmethod
    def id_not_empty(cls, v: str) -> str:
        """Validates that chunk ID is not empty or whitespace."""
        if not v.strip():
            raise ValueError("ID cannot be empty")
        return v


class Chunk(BaseModel):
    """Model representing a parsed markdown chunk with its metadata and source file."""

    text: str
    metadata: ChunkMetadata
    source_file: str


def parse_chunks(md_path: str | Path) -> List[Chunk]:
    """Parses individual markdown files into validated Chunk objects."""
    path = Path(md_path)
    content = path.read_text(encoding="utf-8")
    meta_pattern = re.compile(r'<!--\s*meta\s*\n(.*?)-->', re.DOTALL)

    chunks = []
    last_end = 0

    for match in meta_pattern.finditer(content):
        meta_raw = match.group(1).strip()
        chunk_text = content[last_end:match.start()].strip()
        last_end = match.end()

        if not chunk_text:
            continue

        try:
            meta_dict = yaml.safe_load(meta_raw)
            if not isinstance(meta_dict, dict):
                continue

            validated_meta = ChunkMetadata(**meta_dict)

            chunks.append(Chunk(
                text=chunk_text,
                metadata=validated_meta,
                source_file=path.name
            ))

        except Exception as e:
            print(f"❌ Validation error in {path.name}: {e}")
            continue

    return chunks


def parse_all(directory: str | Path) -> List[Chunk]:
    """Parses all .md files in the specified directory."""
    directory = Path(directory)
    all_chunks = []

    for md_file in sorted(directory.glob("*.md")):
        try:
            file_chunks = parse_chunks(md_file)
            all_chunks.extend(file_chunks)
            print(f"✓  {md_file.name}: {len(file_chunks)} chunks")
        except Exception as e:
            print(f"✗  {md_file.name}: {e}")

    return all_chunks


def validate_all_links(chunks: List[Chunk]) -> List[str]:
    """Validates that all related node references point to existing chunk IDs."""
    all_ids = {c.metadata.id for c in chunks}
    broken_links = []

    for chunk in chunks:
        for ref in chunk.metadata.related_nodes:
            if ref not in all_ids:
                broken_links.append(f"[{chunk.metadata.id}] → '{ref}' not found")

    return broken_links


if __name__ == "__main__":
    chunks = parse_all("../data/grammar_annotated")
    print(f"\nTotal chunks: {len(chunks)}\n")

    if chunks:
        broken = validate_all_links(chunks)
        if broken:
            print(f"🔗 BROKEN LINKS ({len(broken)}):")
            for b in broken:
                print(f"   {b}")
        else:
            print("✅ All related_nodes are valid")

        levels = Counter(c.metadata.level for c in chunks)
        types = Counter(c.metadata.chunk_type for c in chunks)

        print("\n📊 By level:", dict(levels))
        print("📊 By type: ", dict(types))
    else:
        print("📭 No chunks found. Check your directory or regex.")
