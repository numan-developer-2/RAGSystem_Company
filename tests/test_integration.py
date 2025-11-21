"""
Integration tests for RAG system
Run: pytest tests/test_integration.py -v
"""
import pytest
import requests
import json
from pathlib import Path

API_BASE_URL = "http://localhost:8000"
ADMIN_API_KEY = "admin_key_123"
TEST_USER_KEY = None  # Will be generated in setup


class TestIntegration:
    """Integration tests for RAG API"""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment"""
        # Generate test user API key
        response = requests.post(
            f"{API_BASE_URL}/admin/generate-api-key",
            params={"user_id": "test_user", "role": "user", "name": "Test User"},
            headers={"X-API-Key": ADMIN_API_KEY}
        )
        if response.status_code == 200:
            global TEST_USER_KEY
            TEST_USER_KEY = response.json()["api_key"]
    
    def test_health_check(self):
        """Test health endpoint"""
        response = requests.get(f"{API_BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "total_chunks" in data
    
    def test_models_endpoint(self):
        """Test models listing"""
        response = requests.get(f"{API_BASE_URL}/models")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert len(data["models"]) > 0
    
    def test_query_with_auth(self):
        """Test query endpoint with authentication"""
        if not TEST_USER_KEY:
            pytest.skip("Test user key not available")
        
        payload = {
            "question": "What services do you offer?",
            "top_k": 5,
            "temperature": 0.0
        }
        
        response = requests.post(
            f"{API_BASE_URL}/query",
            json=payload,
            headers={"X-API-Key": TEST_USER_KEY}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "answer" in data
        assert "citations" in data
        assert "confidence" in data
        assert isinstance(data["citations"], list)
    
    def test_query_without_auth(self):
        """Test query endpoint without authentication (should fail)"""
        payload = {
            "question": "What services do you offer?",
            "top_k": 5
        }
        
        response = requests.post(
            f"{API_BASE_URL}/query",
            json=payload
        )
        
        assert response.status_code == 401
    
    def test_safe_fail_nonsense_query(self):
        """Test safe-fail with nonsense query"""
        if not TEST_USER_KEY:
            pytest.skip("Test user key not available")
        
        payload = {
            "question": "xyzabc123nonsenseword",
            "top_k": 5
        }
        
        response = requests.post(
            f"{API_BASE_URL}/query",
            json=payload,
            headers={"X-API-Key": TEST_USER_KEY}
        )
        
        assert response.status_code == 200
        data = response.json()
        # Should return safe-fail or low confidence
        assert data["confidence"] < 0.5 or "don't know" in data["answer"].lower()
    
    def test_multiple_queries_consistency(self):
        """Test consistency across multiple queries"""
        if not TEST_USER_KEY:
            pytest.skip("Test user key not available")
        
        test_questions = [
            "What services do you offer?",
            "What is the remote work policy?",
            "Tell me about employee benefits"
        ]
        
        for question in test_questions:
            payload = {
                "question": question,
                "top_k": 5,
                "temperature": 0.0
            }
            
            response = requests.post(
                f"{API_BASE_URL}/query",
                json=payload,
                headers={"X-API-Key": TEST_USER_KEY}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "answer" in data
            assert "citations" in data
    
    def test_admin_endpoints_require_auth(self):
        """Test admin endpoints require admin key"""
        # Try without auth
        response = requests.get(f"{API_BASE_URL}/admin/list-documents")
        assert response.status_code == 401
        
        # Try with user key (should fail)
        if TEST_USER_KEY:
            response = requests.get(
                f"{API_BASE_URL}/admin/list-documents",
                headers={"X-API-Key": TEST_USER_KEY}
            )
            assert response.status_code == 403
        
        # Try with admin key (should succeed)
        response = requests.get(
            f"{API_BASE_URL}/admin/list-documents",
            headers={"X-API-Key": ADMIN_API_KEY}
        )
        assert response.status_code == 200
    
    def test_audit_logging(self):
        """Test audit logging is working"""
        response = requests.get(
            f"{API_BASE_URL}/admin/audit-summary",
            headers={"X-API-Key": ADMIN_API_KEY}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total_queries" in data


class TestDataValidation:
    """Test data integrity"""
    
    def test_index_files_exist(self):
        """Test that index files exist"""
        data_dir = Path("data")
        assert data_dir.exists()
        assert (data_dir / "index.faiss").exists()
        assert (data_dir / "meta.json").exists()
        assert (data_dir / "embeddings.npy").exists()
    
    def test_metadata_valid(self):
        """Test metadata is valid JSON"""
        meta_file = Path("data/meta.json")
        with open(meta_file, 'r') as f:
            metadata = json.load(f)
        
        assert isinstance(metadata, list)
        assert len(metadata) > 0
        
        # Check first chunk has required fields
        first_chunk = metadata[0]
        assert "doc" in first_chunk
        assert "chunk_id" in first_chunk
        assert "text" in first_chunk


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
