"""Request context utilities for correlation and tracing."""

import threading
import uuid
from typing import Optional

_request_context = threading.local()


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return uuid.uuid4().hex[:12]


def set_request_id(request_id: str) -> None:
    """Store request ID in thread-local storage."""
    _request_context.request_id = request_id


def get_request_id() -> Optional[str]:
    """Retrieve current request ID from thread-local storage."""
    return getattr(_request_context, 'request_id', None)


def clear_request_context() -> None:
    """Clear thread-local request context."""
    if hasattr(_request_context, 'request_id'):
        delattr(_request_context, 'request_id')
