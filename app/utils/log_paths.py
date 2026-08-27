from pathlib import Path, PureWindowsPath


DEFAULT_LOG_FILE = "record.log"


def validate_log_file_name(log_file):
    """Validate that LOG_FILE is a file name, not a filesystem path."""
    if log_file is None:
        log_file = DEFAULT_LOG_FILE

    log_file = str(log_file).strip()
    path = Path(log_file)
    windows_path = PureWindowsPath(log_file)

    if (
        not log_file
        or "\x00" in log_file
        or log_file in {".", ".."}
        or path.is_absolute()
        or windows_path.is_absolute()
        or path.name != log_file
        or windows_path.name != log_file
    ):
        raise ValueError("LOG_FILE must be a file name under logs/, not a path")

    return log_file


def resolve_log_file_path(log_file=None, logs_dir="logs"):
    """Return the resolved path for the configured log file under logs/."""
    return Path(logs_dir).resolve() / validate_log_file_name(log_file)
