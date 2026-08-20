"""Shared exceptions for cooperative background work."""


class TaskCancelled(Exception):
    """Raised when a user cancels a cooperative analysis task."""
