"""
Hybrid Retrieval: Combines BM25 (keyword) + Vector Search (semantic)
for better retrieval accuracy
"""
import numpy as np
from typing import List, Dict, Tuple
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, CrossEncoder
import faiss


class HybridRetriever:
    """
    Combines BM25 (keyword-based) and FAISS (semantic) search
    with score fusion for optimal retrieval
    """
    
    def __init__(self, embedding_model: SentenceTransformer, 
                 faiss_index: faiss.Index, 
                 metadata: List[Dict],
                 embeddings: np.ndarray,
                 enable_reranking: bool = True):
        """
        Initialize hybrid retriever
        
        Args:
            embedding_model: Sentence transformer model
            faiss_index: FAISS vector index
            metadata: Document metadata with text
            embeddings: Pre-computed embeddings
            enable_reranking: Whether to use cross-encoder re-ranking
        """
        self.embedding_model = embedding_model
        self.faiss_index = faiss_index
        self.metadata = metadata
        self.embeddings = embeddings
        self.enable_reranking = enable_reranking
        
        # Build BM25 index
        self.corpus = [chunk['text'] for chunk in metadata]
        tokenized_corpus = [doc.lower().split() for doc in self.corpus]
        self.bm25 = BM25Okapi(tokenized_corpus)
        
        # Load re-ranker model if enabled
        if enable_reranking:
            self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        
    def retrieve(self, query: str, top_k: int = 10, 
                 alpha: float = 0.5) -> List[Dict]:
        """
        Hybrid retrieval with score fusion
        
        Args:
            query: User query
            top_k: Number of results to return
            alpha: Weight for vector search (1-alpha for BM25)
                   0.5 = equal weight, 0.7 = more semantic, 0.3 = more keyword
        
        Returns:
            List of retrieved chunks with combined scores
        """
        # 1. BM25 keyword search
        tokenized_query = query.lower().split()
        bm25_scores = self.bm25.get_scores(tokenized_query)
        
        # Normalize BM25 scores to [0, 1]
        if bm25_scores.max() > 0:
            bm25_scores = bm25_scores / bm25_scores.max()
        
        # 2. Vector semantic search
        query_embedding = self.embedding_model.encode([query], convert_to_numpy=True)
        query_embedding = query_embedding.astype("float32")
        query_embedding = query_embedding / (np.linalg.norm(query_embedding, axis=1, keepdims=True) + 1e-10)
        
        distances, indices = self.faiss_index.search(query_embedding, len(self.metadata))
        
        # Convert distances to similarity scores [0, 1]
        vector_scores = 1 / (1 + distances[0])  # Convert distance to similarity
        
        # 3. Combine scores with weighted fusion
        combined_scores = alpha * vector_scores + (1 - alpha) * bm25_scores
        
        # 4. Get top candidates for re-ranking (get more than top_k)
        rerank_k = min(top_k * 3, len(self.metadata))  # Get 3x candidates
        top_indices = np.argsort(combined_scores)[::-1][:rerank_k]
        
        # 5. Re-rank using cross-encoder if enabled
        if self.enable_reranking and hasattr(self, 'reranker'):
            # Prepare pairs for re-ranking
            pairs = [[query, self.metadata[idx]['text']] for idx in top_indices]
            rerank_scores = self.reranker.predict(pairs)
            
            # Sort by rerank scores
            reranked_indices = np.argsort(rerank_scores)[::-1][:top_k]
            final_indices = [top_indices[i] for i in reranked_indices]
            final_rerank_scores = [rerank_scores[i] for i in reranked_indices]
        else:
            final_indices = top_indices[:top_k]
            final_rerank_scores = [None] * top_k
        
        # 6. Build results
        results = []
        for idx, rerank_score in zip(final_indices, final_rerank_scores):
            chunk = self.metadata[idx].copy()
            chunk['score'] = float(combined_scores[idx])
            chunk['bm25_score'] = float(bm25_scores[idx])
            chunk['vector_score'] = float(vector_scores[idx])
            
            if rerank_score is not None:
                chunk['rerank_score'] = float(rerank_score)
                # Use rerank score for relevance classification
                if rerank_score > 0.5:
                    chunk['relevance'] = 'high'
                elif rerank_score > 0.0:
                    chunk['relevance'] = 'medium'
                else:
                    chunk['relevance'] = 'low'
            else:
                # Use combined score for relevance
                if chunk['score'] > 0.7:
                    chunk['relevance'] = 'high'
                elif chunk['score'] > 0.5:
                    chunk['relevance'] = 'medium'
                else:
                    chunk['relevance'] = 'low'
            
            results.append(chunk)
        
        return results
    
    def explain_retrieval(self, query: str, top_k: int = 3) -> str:
        """
        Explain why certain chunks were retrieved
        Useful for debugging and transparency
        """
        results = self.retrieve(query, top_k=top_k)
        
        explanation = f"Query: '{query}'\n\n"
        explanation += "Top Retrieved Chunks:\n"
        explanation += "=" * 60 + "\n\n"
        
        for i, chunk in enumerate(results, 1):
            explanation += f"Rank {i}: {chunk['doc']} (Chunk {chunk['chunk_id']})\n"
            explanation += f"  Combined Score: {chunk['score']:.3f}\n"
            explanation += f"  - Semantic (Vector): {chunk['vector_score']:.3f}\n"
            explanation += f"  - Keyword (BM25): {chunk['bm25_score']:.3f}\n"
            explanation += f"  Relevance: {chunk['relevance']}\n"
            explanation += f"  Preview: {chunk['text'][:150]}...\n"
            explanation += "-" * 60 + "\n\n"
        
        return explanation
