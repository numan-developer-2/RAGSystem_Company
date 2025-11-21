"""
Production-grade error handling and recovery
"""
from typing import Dict, Any, Optional
from loguru import logger
import traceback
from datetime import datetime


class RAGError(Exception):
    """Base exception for RAG system"""
    def __init__(self, message: str, error_code: str = "RAG_ERROR", details: Dict = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()
        super().__init__(self.message)


class APIKeyError(RAGError):
    """API key related errors"""
    def __init__(self, message: str = "API key not configured or invalid"):
        super().__init__(message, "API_KEY_ERROR")


class RateLimitError(RAGError):
    """Rate limit exceeded"""
    def __init__(self, message: str = "Rate limit exceeded. Please try again later"):
        super().__init__(message, "RATE_LIMIT_ERROR")


class DocumentNotFoundError(RAGError):
    """Document or index not found"""
    def __init__(self, message: str = "Required documents or index files not found"):
        super().__init__(message, "DOCUMENT_NOT_FOUND")


class RetrievalError(RAGError):
    """Retrieval pipeline errors"""
    def __init__(self, message: str = "Error during document retrieval"):
        super().__init__(message, "RETRIEVAL_ERROR")


class GenerationError(RAGError):
    """LLM generation errors"""
    def __init__(self, message: str = "Error during answer generation"):
        super().__init__(message, "GENERATION_ERROR")


class ErrorHandler:
    """
    Centralized error handling with logging and recovery
    """
    
    @staticmethod
    def handle_error(error: Exception, context: str = "") -> Dict[str, Any]:
        """
        Handle errors gracefully with logging and user-friendly messages
        
        Args:
            error: The exception that occurred
            context: Additional context about where error occurred
        
        Returns:
            Error response dict
        """
        # Log full error details
        logger.error(f"Error in {context}: {str(error)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Determine error type and response
        if isinstance(error, APIKeyError):
            return {
                "success": False,
                "error_code": "API_KEY_ERROR",
                "error_message": "API key configuration error. Please check your OPENROUTER_API_KEY.",
                "user_message": "System configuration error. Please contact support.",
                "recoverable": False
            }
        
        elif isinstance(error, RateLimitError):
            return {
                "success": False,
                "error_code": "RATE_LIMIT_ERROR",
                "error_message": str(error),
                "user_message": "Too many requests. Please wait a moment and try again.",
                "recoverable": True,
                "retry_after": 60
            }
        
        elif isinstance(error, DocumentNotFoundError):
            return {
                "success": False,
                "error_code": "DOCUMENT_NOT_FOUND",
                "error_message": str(error),
                "user_message": "Document index not found. Please run document ingestion first.",
                "recoverable": False
            }
        
        elif isinstance(error, RetrievalError):
            return {
                "success": False,
                "error_code": "RETRIEVAL_ERROR",
                "error_message": str(error),
                "user_message": "Error retrieving relevant information. Please try again.",
                "recoverable": True
            }
        
        elif isinstance(error, GenerationError):
            return {
                "success": False,
                "error_code": "GENERATION_ERROR",
                "error_message": str(error),
                "user_message": "Error generating answer. Please try again or rephrase your question.",
                "recoverable": True
            }
        
        else:
            # Generic error
            return {
                "success": False,
                "error_code": "UNKNOWN_ERROR",
                "error_message": str(error),
                "user_message": "An unexpected error occurred. Please try again.",
                "recoverable": True
            }
    
    @staticmethod
    def log_error_metrics(error: Exception, context: str = ""):
        """Log error for monitoring and analytics"""
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "traceback": traceback.format_exc()
        }
        
        logger.error(f"ERROR_METRICS: {error_data}")
        
        # Could send to monitoring service here
        # e.g., Sentry, DataDog, CloudWatch, etc.
    
    @staticmethod
    def create_fallback_response(question: str, error: Exception) -> str:
        """
        Create a helpful fallback response when generation fails
        """
        return f"""I apologize, but I encountered an error while processing your question: "{question}"

Error: {type(error).__name__}

Please try:
1. Rephrasing your question
2. Asking a more specific question
3. Trying again in a moment

If the problem persists, please contact support."""
