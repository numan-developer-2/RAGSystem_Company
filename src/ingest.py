 # src/ingest.py
import os, json, argparse, re
from pathlib import Path
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
import PyPDF2
from docx import Document as DocxDocument
from tqdm import tqdm
import warnings
from loguru import logger
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID

warnings.filterwarnings('ignore')

# Set environment variable to avoid TensorFlow warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

# Rich console for better output
console = Console()

# ----------------- CONFIG -----------------
class Config:
    CHUNK_SIZE = 800  # Tokens per chunk
    CHUNK_OVERLAP = 150  # Token overlap between chunks
    BATCH_SIZE = 32  # Batch size for embeddings
    MODEL_NAME = "all-mpnet-base-v2"  # Better model for semantic search
    MAX_WORKERS = 4  # Number of parallel workers for processing
    
    # Paths
    SCRIPT_DIR = Path(__file__).parent.resolve()
    PROJECT_ROOT = SCRIPT_DIR.parent
    DATA_DIR = PROJECT_ROOT / "data"
    DOCS_DIR = PROJECT_ROOT / "docs"
    INDEX_FILE = DATA_DIR / "index.faiss"
    META_FILE = DATA_DIR / "meta.json"
    EMB_FILE = DATA_DIR / "embeddings.npy"
    LOG_FILE = DATA_DIR / "ingest.log"
    
    # Initialize logging
    @classmethod
    def setup_logging(cls):
        logger.remove()  # Remove default handler
        logger.add(cls.LOG_FILE, rotation="100 MB", level="INFO")
        logger.add(lambda msg: console.print(msg, style="blue"), level="INFO")

config = Config()

# --------------- UTIL ----------------------
def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def text_from_pdf(path: Path) -> str:
    """Extract text from PDF using PyPDF2 with improved extraction"""
    texts = []
    try:
        with open(path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            total_pages = len(pdf_reader.pages)
            for i, page in enumerate(pdf_reader.pages):
                try:
                    t = page.extract_text()
                    if t and len(t.strip()) > 10:  # Only add if meaningful text
                        # Clean up text
                        t = re.sub(r'\s+', ' ', t)  # Normalize whitespace
                        t = re.sub(r'\n+', '\n', t)  # Remove excessive newlines
                        texts.append(t)
                except Exception as e:
                    print(f"    ⚠️  Error on page {i+1}/{total_pages}: {str(e)[:50]}")
                    continue
    except Exception as e:
        print(f"    ❌ Error reading PDF {path.name}: {e}")
    return "\n\n".join(texts)

def text_from_docx(path: Path) -> str:
    """Extract text from DOCX file"""
    try:
        doc = DocxDocument(path)
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        print(f"Error reading DOCX {path}: {e}")
        return ""

def load_text(path: Path) -> str:
    """Load text from various file formats"""
    suf = path.suffix.lower()
    if suf in ['.txt', '.md']:
        return path.read_text(encoding='utf-8', errors='ignore')
    elif suf == '.pdf':
        return text_from_pdf(path)
    elif suf == '.docx':
        return text_from_docx(path)
    return ""

def chunk_text(text: str, chunk_size=None, overlap=None):
    """Improved chunking with better context preservation and token-based splitting"""
    chunk_size = chunk_size or config.CHUNK_SIZE
    overlap = overlap or config.CHUNK_OVERLAP
    
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        tokenizer = enc.encode
    except ImportError:
        logger.warning("tiktoken not available, falling back to character-based chunking")
        tokenizer = lambda x: list(x)  # Character-based fallback
    
    # Clean text
    text = text.replace("\r\n", "\n")
    text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    
    # Split by paragraphs first
    paras = [p.strip() for p in text.split("\n\n") if p.strip() and len(p.strip()) > 20]
    
    chunks = []
    for p in paras:
        if len(p) <= chunk_size:
            chunks.append(p)
        else:
            # Split long paragraphs by sentences
            sentences = re.split(r'(?<=[.!?])\s+', p)
            current_chunk = ""
            
            for sent in sentences:
                if len(current_chunk) + len(sent) <= chunk_size:
                    current_chunk += " " + sent if current_chunk else sent
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sent
            
            if current_chunk:
                chunks.append(current_chunk.strip())
    
    # Add overlap between chunks for better context
    overlapped_chunks = []
    for i, chunk in enumerate(chunks):
        if i > 0 and overlap > 0:
            # Add last N chars from previous chunk
            prev_chunk = chunks[i-1]
            overlap_text = prev_chunk[-overlap:] if len(prev_chunk) > overlap else prev_chunk
            chunk = overlap_text + " " + chunk
        overlapped_chunks.append(chunk.strip())
    
    # Filter out very small chunks
    return [c for c in overlapped_chunks if len(c) > 50]

# --------------- INGEST & EMBED -------------
def ingest_and_index(docs_dir: Path, model_name: str = None):
    """Main ingestion pipeline with parallel processing and better progress tracking"""
    model_name = model_name or config.MODEL_NAME
    
    if not docs_dir.exists():
        logger.error(f"❌ Documents directory not found at {docs_dir}")
        return
    
    ensure_dir(config.DATA_DIR)
    config.setup_logging()

    logger.info(f"Loading embedder: {model_name}")
    model = SentenceTransformer(model_name)

    meta = []  # list of {chunk_id, doc, start_char(optional), text}
    texts = []
    chunk_id = 0

    logger.info(f"📂 Scanning documents in: {docs_dir}")
    supported_exts = {'.pdf', '.txt', '.md', '.docx'}
    files = [f for f in docs_dir.glob("*") if f.suffix.lower() in supported_exts and f.is_file()]
    
    if not files:
        logger.warning(f"⚠️  No documents found in {docs_dir}")
        logger.info(f"   Supported formats: {', '.join(supported_exts)}")
        return
    
    logger.info(f"📄 Found {len(files)} document(s)")
    
    def process_file(file_path: Path) -> tuple[list, list]:
        local_meta = []
        local_texts = []
        nonlocal chunk_id
        
        logger.info(f"Processing: {file_path.name}")
        txt = load_text(file_path)
        if not txt or len(txt) < 20:
            logger.warning(f"⚠️  Skipping {file_path.name} (no text extracted)")
            return [], []
        
        chunks = chunk_text(txt)
        logger.info(f"✓ Created {len(chunks)} chunks from {file_path.name}")
        
        for chunk in chunks:
            local_meta.append({"chunk_id": chunk_id, "doc": file_path.name, "text": chunk})
            local_texts.append(chunk)
            chunk_id += 1
        
        return local_meta, local_texts
    
    # Process files in parallel
    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
        results = list(executor.map(process_file, sorted(files)))
    
    # Combine results
    for local_meta, local_texts in results:
        meta.extend(local_meta)
        texts.extend(local_texts)

    if not texts:
        logger.error("❌ No text chunks produced. Please check your documents.")
        return
    
    logger.info(f"✅ Total chunks: {len(texts)}")
    logger.info(f"🔄 Generating embeddings (batch size: {config.BATCH_SIZE})...")
    
    # compute embeddings in batches with progress bar
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    ) as progress:
        embs = []
        encode_task = progress.add_task("Encoding chunks...", total=len(texts))
        
        for i in range(0, len(texts), config.BATCH_SIZE):
            batch = texts[i:i+config.BATCH_SIZE]
            emb = model.encode(batch, convert_to_numpy=True, show_progress_bar=False)
            embs.append(emb)
            progress.update(encode_task, advance=len(batch))
            
    embs = np.vstack(embs).astype("float32")
    # normalize
    norms = np.linalg.norm(embs, axis=1, keepdims=True)
    embs = embs / (norms + 1e-10)
    
    # save embeddings & meta
    np.save(str(config.EMB_FILE), embs)
    with open(config.META_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # build faiss index (inner product on normalized = cosine)
    d = embs.shape[1]
    index = faiss.IndexFlatIP(d)
    index.add(embs)
    faiss.write_index(index, str(config.INDEX_FILE))
    
    logger.info("\n" + "="*60)
    logger.info("✨ Ingestion Complete!")
    logger.info("="*60)
    logger.info(f"✅ Index built & saved: {config.INDEX_FILE}")
    logger.info(f"✅ Meta saved: {config.META_FILE}")
    logger.info(f"✅ Embeddings saved: {config.EMB_FILE}")
    logger.info(f"📊 Total vectors: {len(texts)}")
    logger.info(f"📐 Embedding dimension: {d}")
    logger.info("="*60)

# --------------- CLI ------------------------
if __name__ == "__main__":
    config.setup_logging()
    logger.info("="*60)
    logger.info("🚀 RAG Document Ingestion Pipeline")
    logger.info("="*60)
    
    p = argparse.ArgumentParser(description="Ingest documents and create FAISS index")
    p.add_argument("--docs", type=str, default=str(config.DOCS_DIR), help="folder with docs")
    p.add_argument("--model", type=str, default=config.MODEL_NAME, help="Sentence transformer model")
    p.add_argument("--chunk-size", type=int, default=config.CHUNK_SIZE, help="chunk size in tokens")
    p.add_argument("--chunk-overlap", type=int, default=config.CHUNK_OVERLAP, help="chunk overlap in tokens")
    p.add_argument("--batch-size", type=int, default=config.BATCH_SIZE, help="batch size for embeddings")
    args = p.parse_args()
    
    # Update config with CLI args
    config.CHUNK_SIZE = args.chunk_size
    config.CHUNK_OVERLAP = args.chunk_overlap
    config.BATCH_SIZE = args.batch_size
    
    docs_path = Path(args.docs)
    logger.info(f"📂 Documents directory: {docs_path}")
    logger.info(f"🤖 Embedding model: {args.model}")
    logger.info(f"💾 Output directory: {config.DATA_DIR}")
    logger.info(f"📊 Chunk size: {config.CHUNK_SIZE}, Overlap: {config.CHUNK_OVERLAP}")
    logger.info(f"🔄 Batch size: {config.BATCH_SIZE}\n")
    
    ingest_and_index(docs_path, args.model)
