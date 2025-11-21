"""
Unit tests for RAG components
Run: pytest tests/test_unit.py -v
"""
import pytest
import numpy as np
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from hybrid_retriever import HybridRetriever
from cache_manager import CacheManager
from conversation_memory import ConversationMemory


class TestHybridRetriever:
    """Test hybrid retrieval"""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data for testing"""
        from sentence_transformers import SentenceTransformer
        
        model = SentenceTransformer("all-mpnet-base-v2")
        
        texts = [
            "We offer web development services",
            "Our remote work policy allows 3 days per week",
            "Employee benefits include health insurance"
        ]
        
        embeddings = model.encode(texts)
        
        metadata = [
            {"doc": "services.pdf", "chunk_id": 1, "text": texts[0]},
            {"doc": "policy.pdf", "chunk_id": 2, "text": texts[1]},
            {"doc": "benefits.pdf", "chunk_id": 3, "text": texts[2]}
        ]
        
        return model, embeddings, metadata
    
    def test_retrieve_returns_results(self, sample_data):
        """Test that retrieval returns results"""
        model, embeddings, metadata = sample_data
        
        # Create simple FAISS index
        import faiss
        index = faiss.IndexFlatL2(embeddings.shape[1])
        index.add(embeddings.astype('float32'))
        
        retriever = HybridRetriever(model, index, metadata, embeddings)
        
        results = retriever.retrieve("web development", top_k=2)
        
        assert len(results) > 0
        assert len(results) <= 2
        assert "doc" in results[0]
        assert "score" in results[0]


class TestCacheManager:
    """Test caching functionality"""
    
    def test_cache_set_and_get(self):
        """Test cache set and get"""
        cache = CacheManager(ttl=60)
        
        test_data = {"answer": "Test answer", "sources": []}
        cache.set("test question", test_data, "model1")
        
        retrieved = cache.get("test question", "model1")
        
        assert retrieved is not None
        assert retrieved["answer"] == "Test answer"
    
    def test_cache_miss(self):
        """Test cache miss"""
        cache = CacheManager(ttl=60)
        
        retrieved = cache.get("nonexistent question", "model1")
        
        assert retrieved is None
    
    def test_cache_stats(self):
        """Test cache statistics"""
        cache = CacheManager(ttl=60)
        
        cache.set("q1", {"answer": "a1"}, "m1")
        cache.get("q1", "m1")  # Hit
        cache.get("q2", "m1")  # Miss
        
        stats = cache.get_stats()
        
        assert stats["total_entries"] == 1
        assert stats["total_hits"] >= 1


class TestConversationMemory:
    """Test conversation memory"""
    
    def test_add_and_retrieve_turn(self):
        """Test adding and retrieving conversation turns"""
        memory = ConversationMemory(max_turns=3)
        
        memory.add_turn(
            session_id="session1",
            question="What services?",
            answer="We offer web development",
            sources=[]
        )
        
        context = memory.get_context("session1")
        
        assert "What services?" in context
        assert "web development" in context
    
    def test_max_turns_limit(self):
        """Test max turns limit"""
        memory = ConversationMemory(max_turns=2)
        
        memory.add_turn("s1", "Q1", "A1", [])
        memory.add_turn("s1", "Q2", "A2", [])
        memory.add_turn("s1", "Q3", "A3", [])
        
        context = memory.get_context("s1")
        
        # Should only have last 2 turns
        assert "Q3" in context
        assert "Q2" in context
        assert "Q1" not in context


class TestInputValidation:
    """Test input validation"""
    
    def test_question_length_validation(self):
        """Test question length limits"""
        from rate_limiter import InputValidator
        
        validator = InputValidator()
        
        # Too short
        valid, msg = validator.validate_question("")
        assert not valid
        
        # Too long
        valid, msg = validator.validate_question("x" * 2000)
        assert not valid
        
        # Valid
        valid, msg = validator.validate_question("What is the policy?")
        assert valid
    
    def test_parameter_validation(self):
        """Test parameter validation"""
        from rate_limiter import InputValidator
        
        validator = InputValidator()
        
        # Invalid top_k
        valid, msg = validator.validate_parameters(top_k=0, temperature=0.5)
        assert not valid
        
        # Invalid temperature
        valid, msg = validator.validate_parameters(top_k=5, temperature=3.0)
        assert not valid
        
        # Valid
        valid, msg = validator.validate_parameters(top_k=5, temperature=0.7)
        assert valid


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
