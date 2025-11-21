# src/database.py
"""
Database module for analytics and feedback tracking
Uses SQLite for simplicity and portability
"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from loguru import logger

class Database:
    """Handles all database operations for analytics and feedback"""
    
    def __init__(self, db_path: Path = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent / "data" / "analytics.db"
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def _init_db(self):
        """Initialize database schema"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Queries table - track all user queries
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS queries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    sources TEXT,  -- JSON array of sources
                    top_k INTEGER,
                    temperature REAL,
                    model TEXT,
                    execution_time REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    user_ip TEXT,
                    success BOOLEAN DEFAULT 1
                )
            """)
            
            # Feedback table - track user feedback
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_id INTEGER,
                    rating INTEGER,  -- 1 for helpful, -1 for not helpful
                    comment TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (query_id) REFERENCES queries(id)
                )
            """)
            
            # Failed queries table - track queries with no good answer
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS failed_queries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL,
                    error_message TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Document stats table - track document usage
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS document_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_name TEXT NOT NULL,
                    times_retrieved INTEGER DEFAULT 0,
                    last_accessed DATETIME,
                    UNIQUE(doc_name)
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_queries_timestamp 
                ON queries(timestamp)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_queries_success 
                ON queries(success)
            """)
            
            logger.info(f"✅ Database initialized at {self.db_path}")
    
    def log_query(self, question: str, answer: str, sources: List[Dict], 
                  top_k: int, temperature: float, model: str, 
                  execution_time: float, user_ip: str = None, 
                  success: bool = True) -> int:
        """Log a query to the database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO queries 
                (question, answer, sources, top_k, temperature, model, 
                 execution_time, user_ip, success)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                question, answer, json.dumps(sources), top_k, temperature, 
                model, execution_time, user_ip, success
            ))
            
            query_id = cursor.lastrowid
            
            # Update document stats
            for source in sources:
                doc_name = source.get('doc', '')
                cursor.execute("""
                    INSERT INTO document_stats (doc_name, times_retrieved, last_accessed)
                    VALUES (?, 1, CURRENT_TIMESTAMP)
                    ON CONFLICT(doc_name) DO UPDATE SET
                        times_retrieved = times_retrieved + 1,
                        last_accessed = CURRENT_TIMESTAMP
                """, (doc_name,))
            
            return query_id
    
    def log_feedback(self, query_id: int, rating: int, comment: str = None):
        """Log user feedback for a query"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO feedback (query_id, rating, comment)
                VALUES (?, ?, ?)
            """, (query_id, rating, comment))
    
    def log_failed_query(self, question: str, error_message: str = None):
        """Log a failed query"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO failed_queries (question, error_message)
                VALUES (?, ?)
            """, (question, error_message))
    
    def get_analytics(self, days: int = 7) -> Dict[str, Any]:
        """Get analytics for the last N days"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Total queries
            cursor.execute("""
                SELECT COUNT(*) as total
                FROM queries
                WHERE timestamp >= datetime('now', '-' || ? || ' days')
            """, (days,))
            total_queries = cursor.fetchone()['total']
            
            # Successful queries
            cursor.execute("""
                SELECT COUNT(*) as successful
                FROM queries
                WHERE timestamp >= datetime('now', '-' || ? || ' days')
                AND success = 1
            """, (days,))
            successful_queries = cursor.fetchone()['successful']
            
            # Average execution time
            cursor.execute("""
                SELECT AVG(execution_time) as avg_time
                FROM queries
                WHERE timestamp >= datetime('now', '-' || ? || ' days')
            """, (days,))
            avg_time = cursor.fetchone()['avg_time'] or 0
            
            # Most popular questions (top 10)
            cursor.execute("""
                SELECT question, COUNT(*) as count
                FROM queries
                WHERE timestamp >= datetime('now', '-' || ? || ' days')
                GROUP BY question
                ORDER BY count DESC
                LIMIT 10
            """, (days,))
            popular_questions = [dict(row) for row in cursor.fetchall()]
            
            # Most used documents
            cursor.execute("""
                SELECT doc_name, times_retrieved, last_accessed
                FROM document_stats
                ORDER BY times_retrieved DESC
                LIMIT 10
            """)
            popular_docs = [dict(row) for row in cursor.fetchall()]
            
            # Failed queries
            cursor.execute("""
                SELECT question, error_message, timestamp
                FROM failed_queries
                WHERE timestamp >= datetime('now', '-' || ? || ' days')
                ORDER BY timestamp DESC
                LIMIT 10
            """, (days,))
            failed_queries = [dict(row) for row in cursor.fetchall()]
            
            # Feedback stats
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN rating > 0 THEN 1 ELSE 0 END) as positive,
                    SUM(CASE WHEN rating < 0 THEN 1 ELSE 0 END) as negative
                FROM feedback
                WHERE timestamp >= datetime('now', '-' || ? || ' days')
            """, (days,))
            feedback_row = cursor.fetchone()
            feedback_stats = {
                'positive': feedback_row['positive'] or 0,
                'negative': feedback_row['negative'] or 0
            }
            
            return {
                'total_queries': total_queries,
                'successful_queries': successful_queries,
                'success_rate': (successful_queries / total_queries * 100) if total_queries > 0 else 0,
                'avg_execution_time': round(avg_time, 2),
                'popular_questions': popular_questions,
                'popular_documents': popular_docs,
                'failed_queries': failed_queries,
                'feedback': feedback_stats,
                'period_days': days
            }
    
    def get_recent_queries(self, limit: int = 20) -> List[Dict]:
        """Get recent queries"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, question, answer, sources, execution_time, timestamp
                FROM queries
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            queries = []
            for row in cursor.fetchall():
                query = dict(row)
                query['sources'] = json.loads(query['sources']) if query['sources'] else []
                queries.append(query)
            
            return queries
    
    def search_queries(self, search_term: str, limit: int = 10) -> List[Dict]:
        """Search queries by question text"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, question, answer, sources, execution_time, timestamp
                FROM queries
                WHERE question LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (f'%{search_term}%', limit))
            
            queries = []
            for row in cursor.fetchall():
                query = dict(row)
                query['sources'] = json.loads(query['sources']) if query['sources'] else []
                queries.append(query)
            
            return queries
    
    def clear_old_data(self, days: int = 30):
        """Clear data older than N days"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Delete old queries
            cursor.execute("""
                DELETE FROM queries
                WHERE timestamp < datetime('now', '-' || ? || ' days')
            """, (days,))
            
            # Delete old failed queries
            cursor.execute("""
                DELETE FROM failed_queries
                WHERE timestamp < datetime('now', '-' || ? || ' days')
            """, (days,))
            
            logger.info(f"Cleared data older than {days} days")

# Singleton instance
_db_instance = None

def get_db() -> Database:
    """Get database singleton instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
