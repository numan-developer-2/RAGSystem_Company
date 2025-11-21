"""
Production monitoring and observability
"""
import time
import json
from typing import Dict, Any, List
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger
import sqlite3


class PerformanceMonitor:
    """
    Monitor system performance and health metrics
    """
    
    def __init__(self, db_path: str = "data/monitoring.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        
        # In-memory metrics for fast access
        self.current_metrics = {
            'requests_total': 0,
            'requests_success': 0,
            'requests_failed': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'avg_response_time': 0,
            'total_tokens': 0,
            'errors_by_type': {}
        }
    
    def _init_db(self):
        """Initialize monitoring database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Performance metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                metadata TEXT
            )
        """)
        
        # Request logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS request_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                question TEXT,
                response_time REAL,
                success BOOLEAN,
                error_type TEXT,
                cache_hit BOOLEAN,
                tokens_used INTEGER
            )
        """)
        
        # Health checks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS health_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                status TEXT NOT NULL,
                details TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def log_request(self, question: str, response_time: float, success: bool,
                   error_type: str = None, cache_hit: bool = False, 
                   tokens_used: int = 0):
        """Log individual request"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO request_logs 
            (timestamp, question, response_time, success, error_type, cache_hit, tokens_used)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            int(time.time()),
            question[:200],  # Truncate long questions
            response_time,
            success,
            error_type,
            cache_hit,
            tokens_used
        ))
        
        conn.commit()
        conn.close()
        
        # Update in-memory metrics
        self.current_metrics['requests_total'] += 1
        if success:
            self.current_metrics['requests_success'] += 1
        else:
            self.current_metrics['requests_failed'] += 1
            if error_type:
                self.current_metrics['errors_by_type'][error_type] = \
                    self.current_metrics['errors_by_type'].get(error_type, 0) + 1
        
        if cache_hit:
            self.current_metrics['cache_hits'] += 1
        else:
            self.current_metrics['cache_misses'] += 1
        
        # Update average response time
        total = self.current_metrics['requests_total']
        current_avg = self.current_metrics['avg_response_time']
        self.current_metrics['avg_response_time'] = \
            (current_avg * (total - 1) + response_time) / total
        
        self.current_metrics['total_tokens'] += tokens_used
    
    def log_metric(self, metric_name: str, value: float, metadata: Dict = None):
        """Log custom metric"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO performance_metrics (timestamp, metric_name, metric_value, metadata)
            VALUES (?, ?, ?, ?)
        """, (
            int(time.time()),
            metric_name,
            value,
            json.dumps(metadata) if metadata else None
        ))
        
        conn.commit()
        conn.close()
    
    def log_health_check(self, status: str, details: Dict = None):
        """Log health check result"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO health_checks (timestamp, status, details)
            VALUES (?, ?, ?)
        """, (
            int(time.time()),
            status,
            json.dumps(details) if details else None
        ))
        
        conn.commit()
        conn.close()
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current in-memory metrics"""
        total = self.current_metrics['requests_total']
        
        return {
            **self.current_metrics,
            'success_rate': f"{(self.current_metrics['requests_success'] / max(total, 1) * 100):.1f}%",
            'cache_hit_rate': f"{(self.current_metrics['cache_hits'] / max(total, 1) * 100):.1f}%",
            'error_rate': f"{(self.current_metrics['requests_failed'] / max(total, 1) * 100):.1f}%"
        }
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance summary for last N hours"""
        cutoff = int(time.time()) - (hours * 3600)
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Total requests
        cursor.execute("""
            SELECT COUNT(*), AVG(response_time), SUM(tokens_used)
            FROM request_logs
            WHERE timestamp > ?
        """, (cutoff,))
        total, avg_time, total_tokens = cursor.fetchone()
        
        # Success rate
        cursor.execute("""
            SELECT COUNT(*) FROM request_logs
            WHERE timestamp > ? AND success = 1
        """, (cutoff,))
        successful = cursor.fetchone()[0]
        
        # Cache hits
        cursor.execute("""
            SELECT COUNT(*) FROM request_logs
            WHERE timestamp > ? AND cache_hit = 1
        """, (cutoff,))
        cache_hits = cursor.fetchone()[0]
        
        # Error breakdown
        cursor.execute("""
            SELECT error_type, COUNT(*) as count
            FROM request_logs
            WHERE timestamp > ? AND success = 0
            GROUP BY error_type
        """, (cutoff,))
        errors = dict(cursor.fetchall())
        
        # Response time percentiles
        cursor.execute("""
            SELECT response_time FROM request_logs
            WHERE timestamp > ? AND success = 1
            ORDER BY response_time
        """, (cutoff,))
        response_times = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        percentiles = {}
        if response_times:
            import numpy as np
            percentiles = {
                'p50': float(np.percentile(response_times, 50)),
                'p90': float(np.percentile(response_times, 90)),
                'p95': float(np.percentile(response_times, 95)),
                'p99': float(np.percentile(response_times, 99))
            }
        
        return {
            'period_hours': hours,
            'total_requests': total or 0,
            'successful_requests': successful or 0,
            'success_rate': f"{(successful / max(total, 1) * 100):.1f}%",
            'cache_hits': cache_hits or 0,
            'cache_hit_rate': f"{(cache_hits / max(total, 1) * 100):.1f}%",
            'avg_response_time': round(avg_time or 0, 3),
            'response_time_percentiles': percentiles,
            'total_tokens_used': total_tokens or 0,
            'errors_by_type': errors,
            'estimated_cost_usd': (total_tokens or 0) * 0.0375 / 1_000_000
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current system health status"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Last health check
        cursor.execute("""
            SELECT status, details, timestamp
            FROM health_checks
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        result = cursor.fetchone()
        
        # Recent error rate
        cutoff = int(time.time()) - 300  # Last 5 minutes
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as errors
            FROM request_logs
            WHERE timestamp > ?
        """, (cutoff,))
        total, errors = cursor.fetchone()
        
        conn.close()
        
        error_rate = (errors / max(total, 1)) * 100 if total else 0
        
        # Determine health status
        if error_rate > 50:
            status = "critical"
        elif error_rate > 20:
            status = "degraded"
        elif error_rate > 5:
            status = "warning"
        else:
            status = "healthy"
        
        return {
            'status': status,
            'last_check': result[2] if result else None,
            'recent_error_rate': f"{error_rate:.1f}%",
            'details': json.loads(result[1]) if result and result[1] else {}
        }
    
    def cleanup_old_data(self, days: int = 30):
        """Clean up old monitoring data"""
        cutoff = int(time.time()) - (days * 86400)
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM request_logs WHERE timestamp < ?", (cutoff,))
        cursor.execute("DELETE FROM performance_metrics WHERE timestamp < ?", (cutoff,))
        cursor.execute("DELETE FROM health_checks WHERE timestamp < ?", (cutoff,))
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        logger.info(f"Cleaned up {deleted} old monitoring records")
        return deleted
