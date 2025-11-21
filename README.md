# RAGSystem_Company

A production-ready **Retrieval-Augmented Generation (RAG)** system that allows you to ask questions about your documents using state-of-the-art LLMs via OpenRouter API.

## ✨ Features

- 📄 **Multi-format Support**: Process PDF, TXT, MD, and DOCX files
- 🔍 **Semantic Search**: FAISS vector database for fast similarity search
- 🤖 **Multiple LLM Options**: Access to various models through OpenRouter
- 💬 **Beautiful UI**: Interactive Streamlit interface with chat history
- 🐳 **Docker Ready**: Containerized for easy deployment
- 🔒 **Secure**: Environment-based API key management

## 📁 Project Structure

```
rag-openrouter/
├─ docs/                    # Put your company docs here (pdf, txt, md, docx)
├─ data/                    # Generated: index.faiss, embeddings.npy, meta.json
├─ src/
│  ├─ ingest.py            # Document processing and indexing
│  ├─ api_openrouter.py    # RAG engine with OpenRouter integration
│  └─ frontend_streamlit.py # Streamlit web interface
├─ requirements.txt         # Python dependencies
├─ Dockerfile              # Docker configuration
├─ .env                    # Environment variables (create this)
└─ README.md               # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- OpenRouter API key ([Get one here](https://openrouter.ai/))

### Installation

1. **Clone or download this repository**

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   
   Create a `.env` file in the project root:
   ```env
   OPENROUTER_API_KEY=your_api_key_here
   ```

4. **Add your documents**
   
   Place your documents (PDF, TXT, MD, DOCX) in the `docs/` folder:
   ```bash
   # Example
   docs/
   ├─ company_handbook.pdf
   ├─ product_guide.md
   └─ meeting_notes.txt
   ```

5. **Process documents and create index**
   ```bash
   cd src
   python ingest.py
   ```
   
   This will:
   - Read all documents from `docs/`
   - Split them into chunks
   - Generate embeddings
   - Create FAISS index in `data/`

6. **Launch the web interface**
   ```bash
   streamlit run src/frontend_streamlit.py
   ```
   
   Open your browser at `http://localhost:8501`

## 🎯 Usage

### Command Line Interface

**Test the RAG engine directly:**
```bash
cd src
python api_openrouter.py "What is this document about?"
```

### Web Interface

1. Launch the Streamlit app
2. Select your preferred LLM model from the sidebar
3. Adjust parameters (temperature, number of context chunks)
4. Ask questions in the chat interface
5. View sources and retrieved context

### Available Models

The system supports various models through OpenRouter:

- **Llama 3.1 8B** (Free) - Fast and capable
- **Gemini Flash 1.5** - Google's efficient model
- **Mistral 7B** (Free) - Strong open-source model
- **Qwen 2 7B** (Free) - Multilingual support

## 🐳 Docker Deployment

### Build the image
```bash
docker build -t rag-openrouter .
```

### Run the container
```bash
docker run -p 8501:8501 \
  -v $(pwd)/docs:/app/docs \
  -v $(pwd)/data:/app/data \
  -e OPENROUTER_API_KEY=your_api_key_here \
  rag-openrouter
```

### Using Docker Compose

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  rag-app:
    build: .
    ports:
      - "8501:8501"
    volumes:
      - ./docs:/app/docs
      - ./data:/app/data
    environment:
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
    restart: unless-stopped
```

Run with:
```bash
docker-compose up -d
```

## 🔧 Configuration

### Embedding Model

The system uses `all-MiniLM-L6-v2` by default. To change:

Edit `src/ingest.py` and `src/api_openrouter.py`:
```python
self.model = SentenceTransformer('your-model-name')
```

Popular alternatives:
- `all-mpnet-base-v2` (higher quality, slower)
- `paraphrase-multilingual-MiniLM-L12-v2` (multilingual)

### Chunking Parameters

Edit in `src/ingest.py`:
```python
def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50)
```

- `chunk_size`: Words per chunk
- `overlap`: Overlapping words between chunks

### RAG Parameters

Adjust in the Streamlit UI or programmatically:
```python
result = rag.query(
    question="Your question",
    top_k=5,              # Number of context chunks
    model="meta-llama/llama-3.1-8b-instruct:free",
    temperature=0.7       # 0.0 = deterministic, 1.0 = creative
)
```

## 📊 How It Works

1. **Document Ingestion** (`ingest.py`)
   - Reads documents from `docs/` folder
   - Splits text into overlapping chunks
   - Generates embeddings using Sentence Transformers
   - Creates FAISS index for fast retrieval

2. **Query Processing** (`api_openrouter.py`)
   - Converts user question to embedding
   - Searches FAISS index for similar chunks
   - Retrieves top-k most relevant contexts
   - Sends context + question to OpenRouter LLM
   - Returns generated answer with sources

3. **User Interface** (`frontend_streamlit.py`)
   - Beautiful chat interface
   - Model selection and parameter tuning
   - Source citation and context viewing
   - Chat history management

## 🛠️ Troubleshooting

### "Index files not found"
Run `python src/ingest.py` to create the index first.

### "OPENROUTER_API_KEY not found"
Create a `.env` file with your API key or set the environment variable.

### "No documents found"
Add documents to the `docs/` folder and run ingestion again.

### Slow performance
- Reduce `top_k` parameter
- Use a smaller embedding model
- Use a faster LLM model

### Out of memory
- Reduce chunk size in `ingest.py`
- Process fewer documents at once
- Use `faiss-cpu` instead of `faiss-gpu`

## 📈 Performance Tips

1. **Optimize chunk size**: Smaller chunks = more precise, larger chunks = more context
2. **Use appropriate top_k**: 3-5 chunks usually sufficient
3. **Choose right model**: Free models for testing, paid for production
4. **Cache embeddings**: Don't re-run ingestion unless documents change
5. **Monitor API usage**: Track OpenRouter credits

## 🔐 Security Best Practices

- Never commit `.env` file to version control
- Use environment variables for API keys
- Implement rate limiting for production
- Sanitize user inputs
- Use HTTPS in production deployments

## 📝 API Reference

### RAGEngine

```python
from api_openrouter import RAGEngine

# Initialize
rag = RAGEngine(data_dir="./data", api_key="your_key")

# Query
result = rag.query(
    question="Your question",
    top_k=5,
    model="meta-llama/llama-3.1-8b-instruct:free",
    temperature=0.7
)

# Result structure
{
    'success': True,
    'answer': "Generated answer...",
    'sources': ['doc1.pdf', 'doc2.txt'],
    'retrieved_chunks': [...],
    'usage': {'prompt_tokens': 100, 'completion_tokens': 50}
}
```

### DocumentIngestor

```python
from ingest import DocumentIngestor

# Initialize
ingestor = DocumentIngestor(docs_dir="./docs", data_dir="./data")

# Run pipeline
ingestor.run()
```

## 🤝 Contributing

Contributions are welcome! Areas for improvement:

- [ ] Add more document formats (HTML, CSV, etc.)
- [ ] Implement conversation memory
- [ ] Add document upload via UI
- [ ] Support for multiple languages
- [ ] Implement caching layer
- [ ] Add authentication system

## 📄 License

MIT License - feel free to use this project for personal or commercial purposes.

## 🙏 Acknowledgments

- [OpenRouter](https://openrouter.ai/) - LLM API access
- [FAISS](https://github.com/facebookresearch/faiss) - Vector similarity search
- [Sentence Transformers](https://www.sbert.net/) - Text embeddings
- [Streamlit](https://streamlit.io/) - Web interface framework

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review OpenRouter documentation
3. Open an issue on GitHub

---

**Built with ❤️ for the RAG community**

Happy querying! 🚀
