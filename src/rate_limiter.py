"""
Rate limiting to prevent abuse and manage costs
"""
import time
from typing import Dict, Optional
from collections import defaultdict
from datetime import datetime


class RateLimiter:
    """
    Token bucket rate limiter for API requests
    """
    
    def __init__(self, requests_per_minute: int = 60, 
                 requests_per_hour: int = 1000,
                 burst_size: int = 10):
        """
        Initialize rate limiter
        
        Args:
            requests_per_minute: Max requests per minute per user
            requests_per_hour: Max requests per hour per user
            burst_size: Allow burst of N requests
        """
        self.rpm_limit = requests_per_minute
        self.rph_limit = requests_per_hour
        self.burst_size = burst_size
        
        # Track requests per user
        self.minute_buckets: Dict[str, list] = defaultdict(list)
        self.hour_buckets: Dict[str, list] = defaultdict(list)
        self.burst_buckets: Dict[str, int] = defaultdict(int)
        self.last_refill: Dict[str, float] = {}
    
    def is_allowed(self, user_id: str) -> tuple[bool, Optional[str]]:
        """
        Check if request is allowed
        
        Returns:
            (allowed: bool, reason: str)
        """
        now = time.time()
        
        # Refill burst bucket
        if user_id not in self.last_refill:
            self.burst_buckets[user_id] = self.burst_size
            self.last_refill[user_id] = now
        else:
            # Refill at 1 token per second
            elapsed = now - self.last_refill[user_id]
            refill = int(elapsed)
            if refill > 0:
                self.burst_buckets[user_id] = min(
                    self.burst_size,
                    self.burst_buckets[user_id] + refill
                )
                self.last_refill[user_id] = now
        
        # Clean old timestamps
        minute_ago = now - 60
        hour_ago = now - 3600
        
        self.minute_buckets[user_id] = [
            t for t in self.minute_buckets[user_id] if t > minute_ago
        ]
        self.hour_buckets[user_id] = [
            t for t in self.hour_buckets[user_id] if t > hour_ago
        ]
        
        # Check limits
        if len(self.minute_buckets[user_id]) >= self.rpm_limit:
            return False, f"Rate limit exceeded: {self.rpm_limit} requests per minute"
        
        if len(self.hour_buckets[user_id]) >= self.rph_limit:
            return False, f"Rate limit exceeded: {self.rph_limit} requests per hour"
        
        if self.burst_buckets[user_id] <= 0:
            return False, "Burst limit exceeded. Please slow down."
        
        # Allow request
        self.minute_buckets[user_id].append(now)
        self.hour_buckets[user_id].append(now)
        self.burst_buckets[user_id] -= 1
        
        return True, None
    
    def get_limits(self, user_id: str) -> Dict:
        """Get current limits for user"""
        now = time.time()
        minute_ago = now - 60
        hour_ago = now - 3600
        
        minute_requests = len([t for t in self.minute_buckets[user_id] if t > minute_ago])
        hour_requests = len([t for t in self.hour_buckets[user_id] if t > hour_ago])
        
        return {
            'requests_last_minute': minute_requests,
            'requests_last_hour': hour_requests,
            'rpm_limit': self.rpm_limit,
            'rph_limit': self.rph_limit,
            'burst_tokens_remaining': self.burst_buckets.get(user_id, self.burst_size),
            'burst_size': self.burst_size
        }


class InputValidator:
    """
    Validate and sanitize user inputs
    """
    
    @staticmethod
    def validate_question(question: str) -> tuple[bool, Optional[str]]:
        """
        Validate user question
        
        Returns:
            (valid: bool, error_message: str)
        """
        if not question or not question.strip():
            return False, "Question cannot be empty"
        
        if len(question) < 3:
            return False, "Question too short (minimum 3 characters)"
        
        if len(question) > 1000:
            return False, "Question too long (maximum 1000 characters)"
        
        # Check for suspicious patterns
        suspicious_patterns = [
            'DROP TABLE',
            'DELETE FROM',
            '<script>',
            'javascript:',
            'eval(',
            'exec('
        ]
        
        question_upper = question.upper()
        for pattern in suspicious_patterns:
            if pattern in question_upper:
                return False, "Invalid characters detected in question"
        
        return True, None
    
    @staticmethod
    def sanitize_question(question: str) -> str:
        """Sanitize user input"""
        # Remove leading/trailing whitespace
        question = question.strip()
        
        # Remove multiple spaces
        question = ' '.join(question.split())
        
        # Remove control characters
        question = ''.join(char for char in question if ord(char) >= 32 or char == '\n')
        
        return question
    
    @staticmethod
    def validate_parameters(top_k: int, temperature: float) -> tuple[bool, Optional[str]]:
        """Validate query parameters"""
        if not isinstance(top_k, int) or top_k < 1 or top_k > 20:
            return False, "top_k must be between 1 and 20"
        
        if not isinstance(temperature, (int, float)) or temperature < 0 or temperature > 2:
            return False, "temperature must be between 0 and 2"
        
        return True, None
