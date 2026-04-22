from __future__ import annotations

class AIBaseException(Exception):
    """Base exception for all AI domain errors."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.details = details or {}

class AIProcessingError(AIBaseException):
    """Raised when the LLM or AI pipeline fails to process a request."""
    pass

class ModelTimeoutError(AIBaseException):
    """Raised when the underlying AI model times out."""
    pass

class VectorStoreError(AIBaseException):
    """Raised when interacting with the Vector Database (Qdrant) fails."""
    pass

class InvalidTaskStateError(AIBaseException):
    """Raised when a task transitions to an invalid state."""
    pass
