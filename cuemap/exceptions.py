"""Exceptions."""


class CueMapError(Exception):
    """Base exception."""
    pass


class ConnectionError(CueMapError):
    """Connection failed."""
    pass


class AuthenticationError(CueMapError):
    """Authentication failed."""
    pass
