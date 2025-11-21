"""
Performance optimization utilities
- Connection pooling
- Batch processing
- Response compression
- Query optimization
"""
import asyncio
import time
from typing import List, Dict, Any
from functools import lru_cache
import hashlib


class QueryOptimizer:
    """Optimize query processing for better performance"""
    
    def __init__(self):
        self.query_cache = {}
        self.embedding_cache = {}
    
    @lru_cache(maxsize=1000)
    def normalize_query(self, query: str) -> str:
        """Normalize query for better caching"""
        # Remove extra spaces
        query = ' '.join(query.split())
        # Lowercase for consistency
        query = query.lower().strip()
        return query
    
    def get_query_hash(self, query: str, model: str = None) -> str:
        """Generate hash for query caching"""
        key = f"{self.normalize_query(query)}_{model or 'default'}"
        return hashlib.md5(key.encode()).hexdigest()
    
    def should_use_cache(self, query: str, force_fresh: bool = False) -> bool:
        """Determine if cache should be used"""
        if force_fresh:
            return False
        
        # Don't cache very short queries
        if len(query.strip()) < 5:
            return False
        
        # Don't cache time-sensitive queries
        time_keywords = ['today', 'now', 'current', 'latest', 'recent']
        query_lower = query.lower()
        if any(keyword in query_lower for keyword in time_keywords):
            return False
        
        return True


class BatchProcessor:
    """Process multiple queries efficiently"""
    
    def __init__(self, batch_size: int = 10, timeout: float = 5.0):
        self.batch_size = batch_size
        self.timeout = timeout
        self.queue = []
        self.results = {}
    
    async def add_query(self, query_id: str, query: str) -> Any:
        """Add query to batch"""
        self.queue.append((query_id, query))
        
        # Process if batch is full
        if len(self.queue) >= self.batch_size:
            await self.process_batch()
        
        # Wait for result
        start = time.time()
        while query_id not in self.results:
            if time.time() - start > self.timeout:
                raise TimeoutError(f"Query {query_id} timeout")
            await asyncio.sleep(0.1)
        
        result = self.results.pop(query_id)
        return result
    
    async def process_batch(self):
        """Process queued queries in batch"""
        if not self.queue:
            return
        
        batch = self.queue[:self.batch_size]
        self.queue = self.queue[self.batch_size:]
        
        # Process batch (implement actual processing here)
        for query_id, query in batch:
            # Placeholder - actual processing would go here
            self.results[query_id] = {"processed": True, "query": query}


class ResponseCompressor:
    """Compress responses to reduce bandwidth"""
    
    @staticmethod
    def compress_sources(sources: List[Dict]) -> List[Dict]:
        """Compress source information"""
        compressed = []
        for source in sources:
            compressed.append({
                'doc': source.get('doc', '').split('/')[-1],  # Just filename
                'relevance': source.get('relevance', 'medium'),
                'score': round(source.get('score', 0), 3)
                # Remove text_preview to save bandwidth
            })
        return compressed
    
    @staticmethod
    def compress_response(response: Dict) -> Dict:
        """Compress full response"""
        compressed = {
            'success': response.get('success'),
            'answer': response.get('answer'),
            'execution_time': round(response.get('execution_time', 0), 3)
        }
        
        # Only include sources if needed
        if response.get('sources'):
            compressed['sources'] = ResponseCompressor.compress_sources(
                response['sources'][:3]  # Only top 3
            )
        
        return compressed


class PerformanceTracker:
    """Track and optimize performance bottlenecks"""
    
    def __init__(self):
        self.timings = {
            'retrieval': [],
            'generation': [],
            'total': []
        }
    
    def record_timing(self, operation: str, duration: float):
        """Record operation timing"""
        if operation in self.timings:
            self.timings[operation].append(duration)
            # Keep only last 100
            if len(self.timings[operation]) > 100:
                self.timings[operation] = self.timings[operation][-100:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        stats = {}
        for operation, timings in self.timings.items():
            if timings:
                import numpy as np
                stats[operation] = {
                    'avg': float(np.mean(timings)),
                    'p50': float(np.percentile(timings, 50)),
                    'p95': float(np.percentile(timings, 95)),
                    'p99': float(np.percentile(timings, 99)),
                    'min': float(min(timings)),
                    'max': float(max(timings))
                }
        return stats
    
    def identify_bottlenecks(self) -> List[str]:
        """Identify performance bottlenecks"""
        bottlenecks = []
        stats = self.get_stats()
        
        for operation, metrics in stats.items():
            # If P95 is more than 2x average, it's a bottleneck
            if metrics['p95'] > metrics['avg'] * 2:
                bottlenecks.append(
                    f"{operation}: P95 ({metrics['p95']:.3f}s) >> Avg ({metrics['avg']:.3f}s)"
                )
        
        return bottlenecks


class ConnectionPool:
    """Manage HTTP connection pooling"""
    
    def __init__(self, max_connections: int = 100):
        self.max_connections = max_connections
        self._pool = None
    
    async def get_client(self):
        """Get HTTP client with connection pooling"""
        import httpx
        
        if self._pool is None:
            limits = httpx.Limits(
                max_keepalive_connections=self.max_connections,
                max_connections=self.max_connections,
                keepalive_expiry=30.0
            )
            self._pool = httpx.AsyncClient(
                limits=limits,
                timeout=httpx.Timeout(90.0),
                http2=True  # Enable HTTP/2 for better performance
            )
        
        return self._pool
    
    async def close(self):
        """Close connection pool"""
        if self._pool:
            await self._pool.aclose()
            self._pool = None
