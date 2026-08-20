from typing import Any, List


def upload_chunks_to_db(chunks: List[Any], collection: Any, model: Any, chroma_batch_size: int = 50) -> int:
    """Indexes a list of Chunk objects into ChromaDB with proper batching."""
    ids = []
    documents = []
    metadatas = []
    texts_to_embed = []

    print(f"Starting processing of {len(chunks)} chunks for ChromaDB...")

    for chunk in chunks:
        meta_dict = chunk.metadata.model_dump()

        text_to_embed = meta_dict.get("summary_for_retrieval") or chunk.text
        texts_to_embed.append(text_to_embed)

        flat_meta = {}
        for k, v in meta_dict.items():
            if isinstance(v, list):
                flat_meta[k] = ", ".join(str(i) for i in v) if v else ""
            elif v is None:
                flat_meta[k] = ""
            else:
                flat_meta[k] = str(v)

        ids.append(meta_dict["id"])
        documents.append(chunk.text)
        metadatas.append(flat_meta)

    if not ids:
        return collection.count()

    print("Generating embeddings via Gemini API...")
    embeddings = model.encode(texts_to_embed)

    print(f"Generated {len(embeddings)} vectors. Starting step-by-step upload to ChromaDB...")

    total_chunks = len(ids)
    for i in range(0, total_chunks, chroma_batch_size):
        end_idx = min(i + chroma_batch_size, total_chunks)

        collection.add(
            ids=ids[i:end_idx],
            embeddings=embeddings[i:end_idx],
            documents=documents[i:end_idx],
            metadatas=metadatas[i:end_idx]
        )
        print(f"  └─ Uploaded to ChromaDB: {end_idx}/{total_chunks} chunks")

    print(f"✅ Successfully uploaded/updated total chunks: {collection.count()}")
    return collection.count()
