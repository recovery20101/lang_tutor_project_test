from contextlib import asynccontextmanager
import chromadb
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from google.genai import Client

from app.routers import rules, check, auth, user, progress
from app.core.config import settings
from app.core.embeddings import GeminiEmbeddingService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes application state and external services during startup."""
    print("Initializing application resources...")

    app.state.gemini_client = Client(api_key=settings.GEMINI_API_KEY)
    app.state.embedding_model = GeminiEmbeddingService(app.state.gemini_client)

    try:
        app.state.chroma_client = chromadb.PersistentClient(path="./chroma_db_data")
        app.state.collection = app.state.chroma_client.get_or_create_collection("spanish_grammar")
        print("✅ Local ChromaDB successfully loaded from ./chroma_db_data")
    except Exception as e:
        print(f"⚠️ Error initializing local ChromaDB: {e}")
        app.state.chroma_client = None
        app.state.collection = None

    yield
    print("Cleaning up application resources...")


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)


@app.get("/health")
async def health_check():
    """Performs health check on the API."""
    return {"status": "ok"}


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(rules.router, prefix="/api/v1")
app.include_router(check.router, prefix="/api/v1")
app.include_router(user.router, prefix="/api/v1")
app.include_router(progress.router, prefix="/api/v1")
