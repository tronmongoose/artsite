"""
Custom exceptions for Agent Guardrails SDK.
"""


class AuthorizationError(Exception):
    """
    Raised when an authorization request is malformed or cannot be evaluated.

    This exception is used for programmer errors such as:
    - Missing required fields
    - Invalid data types
    - Configuration errors

    Normal authorization denials (e.g., exceeding limits) do NOT raise this exception.
    They simply return False from the authorize() method.
    """
    pass
