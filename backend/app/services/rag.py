import asyncio
import logging
import re
from typing import Any, Dict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


async def get_extended_context(query_text: str, collection: Any, model: Any, user_level: str, n_results: int = 15) -> Dict[str, Any]:
    """Retrieves extended context from ChromaDB using direct ID lookups and semantic search."""
    logging.info(f"RAG: Starting context retrieval for query: '{query_text}', user_level: '{user_level}'")
    levels_map = ["A1", "A2", "B1", "B2"]

    try:
        user_level_index = levels_map.index(user_level)
    except ValueError:
        user_level_index = len(levels_map) - 1

    allowed_levels = levels_map[:user_level_index + 1]
    allowed_levels_set = set(allowed_levels)

    if len(allowed_levels) == 1:
        where_filter = {"level": allowed_levels[0]}
    else:
        where_filter = {"level": {"$in": allowed_levels}}

    all_found_ids = set()
    all_found_documents = []
    all_found_metadatas = []

    chunk_id_pattern = r'esp-gram-\d+(\.\d+)*'
    direct_chunk_id_match = re.search(chunk_id_pattern, query_text)

    if direct_chunk_id_match:
        direct_chunk_id = direct_chunk_id_match.group(0)
        direct_chunk_results = await asyncio.to_thread(
            collection.get,
            ids=[direct_chunk_id],
            where=where_filter,
            include=['documents', 'metadatas']
        )
        if direct_chunk_results['ids']:
            all_found_ids.add(direct_chunk_id)
            all_found_documents.append(direct_chunk_results['documents'][0])
            all_found_metadatas.append(direct_chunk_results['metadatas'][0])

            related_str = direct_chunk_results['metadatas'][0].get('related_nodes', "")
            if isinstance(related_str, str):
                ids = [node.strip() for node in related_str.split(',') if node.strip()]
            elif isinstance(related_str, list):
                ids = [node.strip() for node in related_str if isinstance(node, str) and node.strip()]
            else:
                ids = []

            related_to_direct_chunk = [r_id for r_id in ids if r_id not in all_found_ids]
            if related_to_direct_chunk:
                related_results = await asyncio.to_thread(
                    collection.get,
                    ids=related_to_direct_chunk,
                    where=where_filter,
                    include=['documents', 'metadatas']
                )
                for i in range(len(related_results['ids'])):
                    chunk_level = related_results['metadatas'][i].get('level', '').strip()
                    if chunk_level in allowed_levels_set:
                        all_found_ids.add(related_results['ids'][i])
                        all_found_documents.append(related_results['documents'][i])
                        all_found_metadatas.append(related_results['metadatas'][i])

    embedding_res = model.encode(query_text)
    query_embedding = embedding_res[0] if isinstance(embedding_res, list) and len(embedding_res) > 0 and isinstance(embedding_res[0], list) else embedding_res

    semantic_results = await asyncio.to_thread(
        collection.query,
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where_filter,
        include=['documents', 'metadatas']
    )

    for i in range(len(semantic_results['ids'][0])):
        chunk_level = semantic_results['metadatas'][0][i].get('level', '').strip()
        if chunk_level in allowed_levels_set:
            if semantic_results['ids'][0][i] not in all_found_ids:
                all_found_ids.add(semantic_results['ids'][0][i])
                all_found_documents.append(semantic_results['documents'][0][i])
                all_found_metadatas.append(semantic_results['metadatas'][0][i])

    related_ids_to_fetch_from_semantic = []
    seen_related = set()

    for meta in semantic_results['metadatas'][0]:
        related_str = meta.get('related_nodes', "")
        if isinstance(related_str, str):
            ids = [node.strip() for node in related_str.split(',') if node.strip()]
        elif isinstance(related_str, list):
            ids = [node.strip() for node in related_str if isinstance(node, str) and node.strip()]
        else:
            ids = []

        for r_id in ids:
            if r_id not in all_found_ids and r_id not in seen_related:
                related_ids_to_fetch_from_semantic.append(r_id)
                seen_related.add(r_id)

    if related_ids_to_fetch_from_semantic:
        related_results_semantic = await asyncio.to_thread(
            collection.get,
            ids=list(set(related_ids_to_fetch_from_semantic)),
            where=where_filter,
            include=['documents', 'metadatas']
        )

        for i in range(len(related_results_semantic['ids'])):
            chunk_level = related_results_semantic['metadatas'][i].get('level', '').strip()
            if chunk_level in allowed_levels_set:
                all_found_ids.add(related_results_semantic['ids'][i])
                all_found_documents.append(related_results_semantic['documents'][i])
                all_found_metadatas.append(related_results_semantic['metadatas'][i])

    return {
        'ids': [list(all_found_ids)],
        'documents': [all_found_documents],
        'metadatas': [all_found_metadatas]
    }
