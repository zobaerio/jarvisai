"""Utilities for safely consuming untrusted provider response bodies."""
from __future__ import annotations

import json
from typing import Any

class ResponseTooLargeError(ValueError):
    """Raised when a provider response exceeds its configured byte budget."""


def read_bounded_json(response: Any, max_bytes: int) -> Any:
    """Stream a response into a bounded buffer, decode JSON, and always close it."""
    body = bytearray()
    try:
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            if not isinstance(chunk, bytes):
                raise ValueError("Provider response contained a non-byte chunk")
            body.extend(chunk)
            if len(body) > max_bytes:
                raise ResponseTooLargeError
        return json.loads(body)
    finally:
        response.close()
