"""Shared formatting for CSV exports intended for spreadsheet viewing."""


def csv_safe_cell(value):
    """Keep untrusted formula-like text literal without changing numeric values."""
    if value is None:
        return ""
    if isinstance(value, str) and (
        value.startswith(("\t", "\r", "\n"))
        or value.lstrip().startswith(("=", "+", "-", "@", "＝", "＋", "－", "＠"))
    ):
        return "'" + value
    return value
