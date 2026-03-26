class InvalidCSVError(Exception):
    """Raised when the uploaded file cannot be parsed as a valid CSV."""


class InvalidRowError(Exception):
    """Raised when a single CSV row has missing or malformed fields."""
