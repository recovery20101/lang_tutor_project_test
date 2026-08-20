import asyncio
import re
from typing import List, Optional, Set, Tuple

import chromadb
from google.genai import Client
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models import RuleExplanation
from app.services.llm import generate_explanation

LEVELS = ["A1", "A2", "B1", "B2"]
LEVEL_MAP = {level: i for i, level in enumerate(LEVELS)}
BATCH_SIZE_RULES = settings.BATCH_SIZE_RULES


async def get_chroma_client_and_collection():
    """Initializes and returns ChromaDB client and collection."""
    chroma_host = settings.CHROMA_HOST
    chroma_port = settings.CHROMA_PORT
    print(f"Connecting to ChromaDB at {chroma_host}:{chroma_port}")
    client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
    collection = client.get_or_create_collection("spanish_grammar")
    print("ChromaDB collection 'spanish_grammar' initialized.")
    return client, collection


def get_db_session_factory():
    """Initializes and returns the SQLAlchemy session factory."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    print("SQLAlchemy engine and session factory initialized.")
    return AsyncSessionLocal


async def get_all_unique_chunk_ids(collection) -> Set[str]:
    """Fetches all unique chunk IDs from ChromaDB."""
    print("Fetching all unique chunk IDs from ChromaDB...")
    all_chunks_meta = collection.get(
        ids=None,
        where=None,
        limit=None,
        include=['metadatas']
    )
    unique_ids = {meta['id'] for meta in all_chunks_meta['metadatas'] if 'id' in meta}
    print(f"Found {len(unique_ids)} unique chunk IDs.")
    return unique_ids


def extract_title_from_markdown(markdown_content: str) -> Optional[str]:
    """Extracts and cleans the title from markdown content."""
    match = re.search(r'^\s*#+\s*(.+)', markdown_content, re.MULTILINE)
    if match:
        title = match.group(1).strip()
        title = re.sub(r'(\*\*|__)(.*?)\1', r'\2', title)
        title = re.sub(r'(\*|_)(.*?)\1', r'\2', title)
        title = re.sub(r'`([^`]+)`', r'\1', title)
        title = re.sub(r'^\s*\d+(\.\d+)*\s*', '', title)
        return title.strip()
    return None


def parse_chunk_id_for_sort(chunk_id: str) -> List[int]:
    """Extracts numeric indices from a chunk ID for natural sorting."""
    numbers = re.findall(r'\d+', chunk_id)
    return [int(n) for n in numbers]


async def get_context_for_generation(
    collection,
    main_chunk_id: str,
    target_level: str
) -> Tuple[str, str, str, Optional[str], List[str], Optional[str]]:
    """Gathers context for LLM generation, including main chunk and related nodes."""
    allowed_level_index = LEVEL_MAP[target_level]

    main_chunk_results = collection.get(
        ids=[main_chunk_id],
        include=['documents', 'metadatas']
    )

    if not main_chunk_results['ids']:
        return "", "", "", None, [], None

    main_doc = main_chunk_results['documents'][0]
    main_meta = main_chunk_results['metadatas'][0]

    topic = main_meta.get('topic', 'General')
    subtopic = main_meta.get('subtopic', 'General')
    chunk_type = main_meta.get('chunk_type')
    display_title = extract_title_from_markdown(main_doc)

    context_docs = {main_chunk_id: main_doc}
    processed_ids = {main_chunk_id}

    related_nodes_raw = main_meta.get('related_nodes', [])
    if isinstance(related_nodes_raw, str):
        related_nodes = [node.strip() for node in related_nodes_raw.split(',') if node.strip()]
    elif isinstance(related_nodes_raw, List):
        related_nodes = [node.strip() for node in related_nodes_raw if isinstance(node, str) and node.strip()]
    else:
        related_nodes = []

    ids_to_fetch = [r_id for r_id in related_nodes if r_id not in processed_ids]

    relevant_related_node_ids = []
    if ids_to_fetch:
        related_chunks_results = collection.get(
            ids=ids_to_fetch,
            include=['documents', 'metadatas']
        )
        for i in range(len(related_chunks_results['ids'])):
            r_id = related_chunks_results['ids'][i]
            r_meta = related_chunks_results['metadatas'][i]
            r_doc = related_chunks_results['documents'][i]

            r_level = r_meta.get('level')
            if r_level and LEVEL_MAP.get(r_level, -1) <= allowed_level_index:
                relevant_related_node_ids.append(r_id)
                context_docs[r_id] = r_doc

    full_context_text = f"Main Rule ({main_chunk_id}, Level {main_meta.get('level')}):\n{main_doc}\n\n"
    for cid, doc in context_docs.items():
        if cid != main_chunk_id:
            full_context_text += f"Related Rule ({cid}):\n{doc}\n\n"

    return full_context_text, topic, subtopic, display_title, relevant_related_node_ids, chunk_type


async def cleanup_unnecessary_rules(session_factory, collection):
    print("Starting cleanup of unnecessary RuleExplanation entries...")
    async with session_factory() as session:
        result = await session.execute(select(RuleExplanation))
        all_rules = result.scalars().all()

        rules_to_delete = []
        for rule in all_rules:
            main_chunk_meta_results = collection.get(
                ids=[rule.chunk_id],
                include=['metadatas']
            )

            if not main_chunk_meta_results['ids']:
                print(f"Warning: Original chunk {rule.chunk_id} not found in ChromaDB during cleanup. Skipping cleanup for this entry.")
                continue

            original_chunk_level = main_chunk_meta_results['metadatas'][0].get('level')

            if not original_chunk_level or original_chunk_level not in LEVELS:
                print(f"Warning: Chunk {rule.chunk_id} has invalid or missing original level '{original_chunk_level}'. Skipping cleanup for this entry.")
                continue

            if LEVEL_MAP[rule.level] < LEVEL_MAP[original_chunk_level]:
                rules_to_delete.append(rule)
                print(f"Marked for deletion: {rule.chunk_id} for level {rule.level} (original chunk level was {original_chunk_level}).")

        if rules_to_delete:
            for rule in rules_to_delete:
                await session.delete(rule)
            await session.commit()
            print(f"Deleted {len(rules_to_delete)} unnecessary RuleExplanation entries.")
        else:
            print("No unnecessary RuleExplanation entries found for deletion.")

async def populate_rule_explanations():
    print("Starting population of RuleExplanation table with LLM-generated content...")

    chroma_client, collection = await get_chroma_client_and_collection()
    AsyncSessionLocal = get_db_session_factory()
    gemini_client = Client(api_key=settings.GEMINI_API_KEY)
    print("Gemini client initialized.")

    await cleanup_unnecessary_rules(AsyncSessionLocal, collection)

    unique_chunk_ids = await get_all_unique_chunk_ids(collection)
    failed_generations = []
    generated_count = 0

    print("\n--- Starting initial generation loop ---")
    for chunk_id in sorted(list(unique_chunk_ids)):
        if generated_count >= BATCH_SIZE_RULES:
            print(f"Batch size of {BATCH_SIZE_RULES} reached for rule explanations. Stopping.")
            break

        main_chunk_meta_results = collection.get(
            ids=[chunk_id],
            include=['documents', 'metadatas']
        )
        if not main_chunk_meta_results['ids']:
            continue

        original_chunk_level = main_chunk_meta_results['metadatas'][0].get('level')
        if not original_chunk_level or original_chunk_level not in LEVELS:
            continue

        original_level_index = LEVEL_MAP[original_chunk_level]

        for target_level in LEVELS:
            if generated_count >= BATCH_SIZE_RULES:
                break

            if LEVEL_MAP[target_level] < original_level_index:
                continue

            async with AsyncSessionLocal() as session:
                existing_explanation_query = await session.execute(
                    select(RuleExplanation).where(
                        RuleExplanation.chunk_id == chunk_id,
                        RuleExplanation.level == target_level,
                        RuleExplanation.lang == "en"
                    )
                )
                existing_rule_obj = existing_explanation_query.scalar_one_or_none()

                context_text, topic, subtopic, display_title, relevant_related_node_ids, chunk_type = await get_context_for_generation(
                    collection, chunk_id, target_level
                )

                if not context_text:
                    continue

                related_rules_data = []
                if relevant_related_node_ids:
                    related_rules_query = await session.execute(
                        select(RuleExplanation.chunk_id, RuleExplanation.display_title)
                        .where(
                            RuleExplanation.chunk_id.in_(relevant_related_node_ids),
                            RuleExplanation.level == target_level,
                            RuleExplanation.lang == "en"
                        )
                    )
                    for r_chunk_id, r_display_title in related_rules_query.all():
                        related_rules_data.append({"chunk_id": r_chunk_id, "display_title": r_display_title})

                related_rules_data.sort(key=lambda x: parse_chunk_id_for_sort(x['chunk_id']))

                if existing_rule_obj:
                    # Если запись RuleExplanation существует, обновляем ее поля
                    needs_update = False
                    if not existing_rule_obj.display_title:
                        print(f"Updating display_title for existing rule {chunk_id} at level {target_level}.")
                        existing_rule_obj.display_title = display_title
                        needs_update = True
                    if not existing_rule_obj.related_rules:
                        print(f"Updating related_rules for existing rule {chunk_id} at level {target_level}.")
                        existing_rule_obj.related_rules = related_rules_data
                        needs_update = True

                    if needs_update:
                        try:
                            await session.commit()
                            print(f"Updated existing rule {chunk_id} for level {target_level}.")
                        except Exception as e:
                            await session.rollback()
                            print(f"Error updating existing rule {chunk_id} for level {target_level}: {e}")
                    else:
                        print(f"Skipping {chunk_id} for level {target_level} (already exists with all data).")

                    continue

                print(f"Generating explanation for {chunk_id} at level {target_level}...")

                try:
                    generated_content = await generate_explanation(
                        client=gemini_client,
                        context_text=context_text,
                        target_level=target_level,
                        lang="en",
                        rule_id=chunk_id
                    )

                    async with AsyncSessionLocal() as session_for_insert:
                        new_explanation = RuleExplanation(
                            chunk_id=chunk_id,
                            level=target_level,
                            lang="en",
                            topic=topic,
                            subtopic=subtopic,
                            content=generated_content,
                            display_title=display_title,
                            related_rules=related_rules_data
                        )
                        session_for_insert.add(new_explanation)
                        await session_for_insert.commit()
                        generated_count += 1
                except Exception as e:
                    print(f"Error generating for {chunk_id} at level {target_level}: {e}")
                    failed_generations.append((chunk_id, target_level, 0))

                await asyncio.sleep(2)

    print("\n--- Starting retry loop for failed generations ---")
    max_retries = 3
    retry_delay_seconds = 5

    retries_queue = list(failed_generations)
    failed_generations.clear()

    for current_failed in retries_queue:
        if generated_count >= BATCH_SIZE_RULES:
            print(f"Batch size of {BATCH_SIZE_RULES} reached for rule explanations during retry. Stopping generation.")
            break

        chunk_id, target_level, retry_count = current_failed

        if retry_count >= max_retries:
            print(f"Max retries reached for {chunk_id} at level {target_level}. Skipping.")
            failed_generations.append((chunk_id, target_level, retry_count))
            continue

        print(f"Retrying generation for {chunk_id} at level {target_level} (Attempt {retry_count + 1}/{max_retries})...")

        async with AsyncSessionLocal() as session:
            existing_explanation_query = await session.execute(
                select(RuleExplanation).where(
                    RuleExplanation.chunk_id == chunk_id,
                    RuleExplanation.level == target_level,
                    RuleExplanation.lang == "en"
                )
            )
            existing_rule_obj = existing_explanation_query.scalar_one_or_none()

            context_text, topic, subtopic, display_title, relevant_related_node_ids, chunk_type = await get_context_for_generation(
                collection, chunk_id, target_level
            )

            if not context_text:
                print(f"Warning: No context found for {chunk_id} at level {target_level} during retry. Skipping.")
                failed_generations.append((chunk_id, target_level, retry_count))
                continue

            related_rules_data = []
            if relevant_related_node_ids:
                related_rules_query = await session.execute(
                    select(RuleExplanation.chunk_id, RuleExplanation.display_title)
                    .where(
                        RuleExplanation.chunk_id.in_(relevant_related_node_ids),
                        RuleExplanation.level == target_level,
                        RuleExplanation.lang == "en"
                    )
                )
                for r_chunk_id, r_display_title in related_rules_query.all():
                    related_rules_data.append({"chunk_id": r_chunk_id, "display_title": r_display_title})

            related_rules_data.sort(key=lambda x: parse_chunk_id_for_sort(x['chunk_id']))

            if existing_rule_obj:
                needs_update = False
                if not existing_rule_obj.display_title:
                    print(f"Updating display_title for existing rule {chunk_id} at level {target_level} during retry.")
                    existing_rule_obj.display_title = display_title
                    needs_update = True
                if not existing_rule_obj.related_rules:
                    print(f"Updating related_rules for existing rule {chunk_id} at level {target_level} during retry.")
                    existing_rule_obj.related_rules = related_rules_data
                    needs_update = True

                if needs_update:
                    try:
                        await session.commit()
                        print(f"Updated existing rule {chunk_id} for level {target_level} during retry.")
                    except Exception as e:
                        await session.rollback()
                        print(f"Error updating existing rule {chunk_id} for level {target_level} during retry: {e}")
                else:
                    print(f"Skipping {chunk_id} for level {target_level} (already exists with all data).")

                continue

        try:
            generated_content = await generate_explanation(
                client=gemini_client,
                context_text=context_text,
                target_level=target_level,
                lang="en",
                rule_id=chunk_id
            )
            print(f"Successfully generated on retry for {chunk_id} at level {target_level}.")

            async with AsyncSessionLocal() as session_for_insert:
                try:
                    new_explanation = RuleExplanation(
                        chunk_id=chunk_id,
                        level=target_level,
                        lang="en",
                        topic=topic,
                        subtopic=subtopic,
                        content=generated_content,
                        display_title=display_title,
                        related_rules=related_rules_data
                    )
                    session_for_insert.add(new_explanation)
                    await session_for_insert.flush()

                    await session_for_insert.commit()
                    print(f"Saved {chunk_id} for level {target_level} to PostgreSQL on retry.")
                    generated_count += 1
                except Exception as e:
                    await session_for_insert.rollback()
                    print(f"Error saving {chunk_id} for level {target_level} to PostgreSQL on retry: {e}")
                finally:
                    await session_for_insert.close()

        except Exception as e:
            print(f"Retry failed for {chunk_id} at level {target_level}: {e}. Re-adding to retry list.")
            retries_queue.append((chunk_id, target_level, retry_count + 1))

        await asyncio.sleep(retry_delay_seconds)

    print("\n--- RuleExplanation table population complete. ---")
    if failed_generations:
        print(f"WARNING: {len(failed_generations)} items failed to generate after all retries.")
        for item in failed_generations:
            print(f"  - Chunk ID: {item[0]}, Level: {item[1]}")
    else:
        print("All rule explanations generated and saved successfully!")

if __name__ == "__main__":
    asyncio.run(populate_rule_explanations())
