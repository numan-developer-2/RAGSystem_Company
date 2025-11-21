"""
Intelligent Caching System: Reduces API calls and improves response time
for frequently asked questions
"""
import hashlib
import json
import time
from typing import Optional, Dict, Any
from pathlib import Path
import sqlite3
from datetime import datetime, timedelta


class CacheManager:
    """
    Manages response caching with TTL (Time To Live)
    and similarity-based cache hits
    """
    
    def __init__(self, cache_dir: str = "data/cache", ttl_hours: int = 24):
        """
        Initialize cache manager
        
        Args:
            cache_dir: Directory to store cache
            ttl_hours: Cache validity in hours
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_path = self.cache_dir / "cache.db"
        self.ttl_seconds = ttl_hours * 3600
        
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database for cache"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                query_hash TEXT PRIMARY KEY,
                query_text TEXT NOT NULL,
                response TEXT NOT NULL,
                model TEXT,
                timestamp INTEGER NOT NULL,
                hit_count INTEGER DEFAULT 1,
                last_accessed INTEGER
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON cache(timestamp)
        """)
        
        conn.commit()
        conn.close()
    
    def _hash_query(self, query: str, model: str = None) -> str:
        """Generate hash for query"""
        key = f"{query.lower().strip()}_{model or 'default'}"
        return hashlib.md5(key.encode()).hexdigest()
    
    def get(self, query: str, model: str = None) -> Optional[Dict[str, Any]]:
        """
        Get cached response if available and valid
        
        Args:
            query: User query
            model: Model name
        
        Returns:
            Cached response or None
        """
        query_hash = self._hash_query(query, model)
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT response, timestamp, hit_count
            FROM cache
            WHERE query_hash = ?
        """, (query_hash,))
        
        result = cursor.fetchone()
        
        if result:
            response_json, timestamp, hit_count = result
            
            # Check if cache is still valid
            age = time.time() - timestamp
            if age < self.ttl_seconds:
                # Update hit count and last accessed
                cursor.execute("""
                    UPDATE cache
                    SET hit_count = hit_count + 1,
                        last_accessed = ?
                    WHERE query_hash = ?
                """, (int(time.time()), query_hash))
                conn.commit()
                conn.close()
                
                response = json.loads(response_json)
                response['from_cache'] = True
                response['cache_age_seconds'] = int(age)
                response['cache_hit_count'] = hit_count + 1
                
                return response
            else:
                # Cache expired, delete it
                cursor.execute("DELETE FROM cache WHERE query_hash = ?", (query_hash,))
                conn.commit()
        
        conn.close()
        return None
    
    def set(self, query: str, response: Dict[str, Any], model: str = None):
        """
        Cache a response
        
        Args:
            query: User query
            response: Response to cache
            model: Model name
        """
        query_hash = self._hash_query(query, model)
        response_json = json.dumps(response)
        timestamp = int(time.time())
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO cache 
            (query_hash, query_text, response, model, timestamp, last_accessed)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (query_hash, query, response_json, model or 'default', timestamp, timestamp))
        
        conn.commit()
        conn.close()
    
    def clear_expired(self):
        """Remove expired cache entries"""
        cutoff = int(time.time()) - self.ttl_seconds
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM cache WHERE timestamp < ?", (cutoff,))
        deleted = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return deleted
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Total entries
        cursor.execute("SELECT COUNT(*) FROM cache")
        total = cursor.fetchone()[0]
        
        # Total hits
        cursor.execute("SELECT SUM(hit_count) FROM cache")
        total_hits = cursor.fetchone()[0] or 0
        
        # Most popular queries
        cursor.execute("""
            SELECT query_text, hit_count
            FROM cache
            ORDER BY hit_count DESC
            LIMIT 5
        """)
        popular = cursor.fetchall()
        
        # Cache size
        cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
        size_bytes = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_entries': total,
            'total_hits': total_hits,
            'cache_size_mb': size_bytes / (1024 * 1024),
            'popular_queries': [{'query': q, 'hits': h} for q, h in popular],
            'hit_rate': f"{(total_hits / max(total, 1)):.1f}x average"
        }
    
    def clear_all(self):
        """Clear entire cache"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cache")
        conn.commit()
        conn.close()
