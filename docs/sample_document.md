# Sample Document

This is a sample document to help you get started with the RAG Q&A system.

## What is RAG?

Retrieval-Augmented Generation (RAG) is an AI framework that combines:

1. **Information Retrieval**: Finding relevant documents or passages
2. **Language Generation**: Using LLMs to generate natural language responses

## How This System Works

### Document Processing
- Your documents are split into smaller chunks
- Each chunk is converted to a vector embedding
- Embeddings are stored in a FAISS index for fast retrieval

### Query Processing
- Your question is converted to an embedding
- Similar document chunks are retrieved
- Retrieved context is sent to an LLM
- The LLM generates an answer based on the context

## Getting Started

1. Add your documents to the `docs/` folder
2. Run `python src/ingest.py` to process them
3. Launch the web interface with `streamlit run src/frontend_streamlit.py`
4. Start asking questions!

## Tips for Best Results

- Use specific questions rather than vague ones
- The system works best with factual questions about your documents
- Adjust the number of context chunks if answers seem incomplete
- Try different models to find the best balance of speed and quality

## Example Questions

- "What are the main topics covered in this document?"
- "Can you summarize the key points about RAG?"
- "How does the document processing work?"

Replace this sample document with your own documents to get started!
