"""Shared service-layer exceptions."""


class NotebookNotFoundError(Exception):
    """Raised when the target notebook does not exist."""


class QueryLogInsertError(Exception):
    """Raised when persisting a query_logs row fails."""
