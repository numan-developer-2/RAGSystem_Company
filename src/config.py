# src/config.py
"""
Configuration settings for RAG system with tuning knobs
"""
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Paths
    SCRIPT_DIR = Path(__file__).parent.resolve()
    PROJECT_ROOT = SCRIPT_DIR.parent
    DATA_DIR = PROJECT_ROOT / "data"
    INDEX_FILE = DATA_DIR / "index.faiss"
    META_FILE = DATA_DIR / "meta.json"
    EMB_FILE = DATA_DIR / "embeddings.npy"
    LOG_FILE = DATA_DIR / "api.log"
    DOCS_DIR = PROJECT_ROOT / "docs"

    # API Keys
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    ADMIN_API_TOKEN = os.getenv("ADMIN_API_TOKEN", "admin_key_123")

    # Model settings
    EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
    DEFAULT_LLM = "google/gemini-pro-1.5"
    MODEL_NAME = "all-mpnet-base-v2"  # Better model for semantic search
    CHUNK_SIZE = 800  # Tokens per chunk
    CHUNK_OVERLAP = 150  # Token overlap between chunks
    BATCH_SIZE = 32  # Batch size for embeddings
    TOP_K = 5  # Number of chunks to retrieve

    # Retrieval settings
    DEFAULT_TOP_K = 5  # Start 5; try 3-10
    RERANKER_TOP_N = 50  # Search top 50 then rerank to top_k
    RETRIEVAL_CONFIDENCE_THRESHOLD = 0.22  # Tune against validation set

    # Generation settings
    TEMPERATURE_POLICY = 0.0  # For policy/compliance answers
    TEMPERATURE_CONVERSATIONAL = 0.2  # For natural language
    MAX_TOKENS = 512  # Safety limit

    # OpenRouter settings
    OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
    OPENROUTER_KEY = os.getenv("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")
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free")
    MAX_PROMPT_TOKENS = 3000
    
    # API settings
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds
    REQUEST_TIMEOUT = 60  # seconds
    
    @classmethod
    def validate(cls):
        """Validate configuration settings"""
        if not cls.OPENROUTER_KEY:
            raise ValueError("OPENROUTER_API_KEY not set in environment. Please set it in .env file.")
        if not cls.DATA_DIR.exists():
            raise ValueError(f"Data directory not found at {cls.DATA_DIR}")
        if not all(f.exists() for f in [cls.INDEX_FILE, cls.META_FILE, cls.EMB_FILE]):
            raise ValueError("Index files missing. Run ingest.py first.")

config = Config()