"""Controlled errors safe to display without provider payloads."""


class AppError(Exception):
    """An actionable message that contains no private provider data."""
