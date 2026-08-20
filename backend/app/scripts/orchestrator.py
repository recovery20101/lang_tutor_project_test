import chromadb
from google.genai import Client

from app.core.config import settings
from app.core.embeddings import GeminiEmbeddingService
from app.scripts.parse_check import parse_all
from app.scripts.upload_to_chroma import upload_chunks_to_db

# Initialize Gemini API client and embedding service
print("Initializing Gemini API and connecting to ChromaDB...")
gemini_client = Client(api_key=settings.GEMINI_API_KEY)
embedding_service = GeminiEmbeddingService(gemini_client)

# Connect to ChromaDB
client = chromadb.PersistentClient(path="./chroma_db_data")

# Delete existing collection if it exists
try:
    client.delete_collection("spanish_grammar")
    print("Old collection 'spanish_grammar' successfully deleted.")
except Exception as e:
    print(f"Old collection not found or already deleted: {e}")

# Create a new clean collection
collection = client.get_or_create_collection("spanish_grammar")
print("Initialization completed.")


def run_pipeline() -> None:
    """Runs the full data parsing and ChromaDB upload pipeline."""
    print(f"Starting parsing data from directory: {settings.DATA_PATH}...")
    chunks = parse_all(settings.DATA_PATH)
    print(f"Parsing completed. Found chunks: {len(chunks)}")

    if chunks:
        upload_chunks_to_db(chunks, collection, embedding_service)
        print("Data successfully re-imported into ChromaDB!")


if __name__ == "__main__":
    run_pipeline()
