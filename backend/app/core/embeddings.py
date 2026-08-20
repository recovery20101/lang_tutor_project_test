import logging
import time
from google import genai
from google.genai import Client
from google.genai.errors import APIError

logger = logging.getLogger(__name__)


class GeminiEmbeddingService:
    def __init__(
        self,
        client_or_key: Client | str,
        model_name: str = "gemini-embedding-2",
    ):
        if isinstance(client_or_key, str):
            self.client = genai.Client(api_key=client_or_key)
        elif isinstance(client_or_key, Client):
            self.client = client_or_key
        else:
            raise TypeError(f"Expected Client or str, got {type(client_or_key)}")

        self.model_name = model_name.replace("models/", "")

    def _embed_batch_with_retry(self, batch: list[str], max_retries: int = 5) -> list[list[float]]:
        """Sends a batch with guaranteed vector extraction for every element."""
        delay = 15.0
        for attempt in range(max_retries):
            try:
                response = self.client.models.embed_content(
                    model=self.model_name,
                    contents=batch,
                )

                extracted_vectors = []

                if hasattr(response, "embeddings") and response.embeddings:
                    for item in response.embeddings:
                        if hasattr(item, "values"):
                            extracted_vectors.append(list(item.values))
                        elif isinstance(item, (list, tuple)):
                            extracted_vectors.append(list(item))

                elif hasattr(response, "embedding") and response.embedding:
                    emb = response.embedding
                    if hasattr(emb, "values"):
                        extracted_vectors.append(list(emb.values))

                if len(batch) > 1 and len(extracted_vectors) != len(batch):
                    extracted_vectors = []
                    for single_text in batch:
                        single_res = self.client.models.embed_content(
                            model=self.model_name,
                            contents=single_text,
                        )
                        if hasattr(single_res, "embedding") and hasattr(single_res.embedding, "values"):
                            extracted_vectors.append(list(single_res.embedding.values))
                        elif hasattr(single_res, "embeddings") and single_res.embeddings:
                            extracted_vectors.append(list(single_res.embeddings[0].values))
                        time.sleep(0.1)

                return extracted_vectors

            except APIError as e:
                if getattr(e, "code", None) == 429 or "429" in str(e):
                    logger.warning(
                        f"Rate limit TPM/RPM exceeded (429). Waiting {delay}s... (attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(delay)
                    delay += 10.0
                else:
                    raise e

        raise RuntimeError("Failed to retrieve embeddings due to API rate limits.")

    def encode(
        self,
        sentences: str | list[str],
        batch_size: int = 25,
        pause_between_batches: float = 3.5,
    ) -> list[float] | list[list[float]]:
        if isinstance(sentences, str):
            res = self._embed_batch_with_retry([sentences])
            return res[0] if res else []

        if not sentences:
            return []

        all_embeddings = []
        total_batches = (len(sentences) + batch_size - 1) // batch_size

        for i in range(0, len(sentences), batch_size):
            current_batch_num = (i // batch_size) + 1
            batch = sentences[i : i + batch_size]

            logger.info(f"Processing batch {current_batch_num}/{total_batches} ({len(batch)} chunks)...")
            batch_vectors = self._embed_batch_with_retry(batch)

            for vec in batch_vectors:
                all_embeddings.append(vec)

            if i + batch_size < len(sentences):
                time.sleep(pause_between_batches)

        return all_embeddings