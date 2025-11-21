"""
Audit Logger for Compliance and Security
Logs all queries, responses, and retrieved chunks
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from loguru import logger


class AuditLogger:
    """Log all queries for compliance and audit purposes"""
    
    def __init__(self, audit_dir: str = "data/audit"):
        self.audit_dir = Path(audit_dir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        
        # Daily audit log file
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        self.audit_file = self.audit_dir / f"audit_{self.current_date}.jsonl"
        
        logger.info(f"Audit logger initialized: {self.audit_file}")
    
    def _rotate_if_needed(self):
        """Rotate log file if date changed"""
        current_date = datetime.now().strftime("%Y-%m-%d")
        if current_date != self.current_date:
            self.current_date = current_date
            self.audit_file = self.audit_dir / f"audit_{self.current_date}.jsonl"
            logger.info(f"Rotated audit log to: {self.audit_file}")
    
    def log_query(
        self,
        query_id: str,
        user_id: str,
        user_role: str,
        question: str,
        answer: str,
        retrieved_chunks: List[Dict],
        model_used: str,
        success: bool,
        response_time: float,
        tokens_used: Optional[Dict] = None,
        error: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """
        Log query with full details for audit trail
        """
        self._rotate_if_needed()
        
        # Build audit entry
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "query_id": query_id,
            "user": {
                "user_id": user_id,
                "role": user_role,
                "ip_address": ip_address
            },
            "query": {
                "question": question,
                "question_length": len(question)
            },
            "response": {
                "answer": answer,
                "answer_length": len(answer),
                "success": success,
                "error": error
            },
            "retrieval": {
                "num_chunks": len(retrieved_chunks),
                "sources": [
                    {
                        "doc": chunk.get("doc"),
                        "chunk_id": chunk.get("chunk_id"),
                        "score": chunk.get("score"),
                        "text_preview": chunk.get("text", "")[:100]
                    }
                    for chunk in retrieved_chunks[:5]  # Log top 5 only
                ]
            },
            "model": {
                "model_used": model_used,
                "tokens_used": tokens_used or {}
            },
            "performance": {
                "response_time": response_time
            }
        }
        
        # Write to JSONL file (one JSON object per line)
        try:
            with open(self.audit_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(audit_entry) + '\n')
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
    
    def get_audit_summary(self, date: Optional[str] = None) -> Dict:
        """Get audit summary for a specific date"""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        audit_file = self.audit_dir / f"audit_{date}.jsonl"
        
        if not audit_file.exists():
            return {
                "date": date,
                "total_queries": 0,
                "message": "No audit log for this date"
            }
        
        # Parse audit log
        total_queries = 0
        successful_queries = 0
        failed_queries = 0
        users = set()
        models_used = {}
        
        try:
            with open(audit_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        entry = json.loads(line)
                        total_queries += 1
                        
                        if entry["response"]["success"]:
                            successful_queries += 1
                        else:
                            failed_queries += 1
                        
                        users.add(entry["user"]["user_id"])
                        
                        model = entry["model"]["model_used"]
                        models_used[model] = models_used.get(model, 0) + 1
        
        except Exception as e:
            logger.error(f"Error reading audit log: {e}")
            return {"error": str(e)}
        
        return {
            "date": date,
            "total_queries": total_queries,
            "successful_queries": successful_queries,
            "failed_queries": failed_queries,
            "success_rate": f"{(successful_queries / total_queries * 100):.1f}%" if total_queries > 0 else "0%",
            "unique_users": len(users),
            "models_used": models_used
        }
    
    def search_audit_logs(
        self,
        user_id: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Search audit logs with filters"""
        results = []
        
        # Get all audit files in date range
        audit_files = sorted(self.audit_dir.glob("audit_*.jsonl"))
        
        for audit_file in audit_files:
            try:
                with open(audit_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            entry = json.loads(line)
                            
                            # Apply filters
                            if user_id and entry["user"]["user_id"] != user_id:
                                continue
                            
                            results.append(entry)
                            
                            if len(results) >= limit:
                                return results
            
            except Exception as e:
                logger.error(f"Error reading {audit_file}: {e}")
                continue
        
        return results
