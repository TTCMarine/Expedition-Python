"""Exceptions and warnings raised by Expedition-Python."""


class ExpeditionAPIError(Exception):
    """Raised when the loaded ExpDLL does not export a function required for an API."""


class ExpeditionLoadError(OSError):
    """Raised when ExpDLL.dll cannot be found, is the wrong architecture, or cannot be loaded."""


class ExpeditionNotRunningError(RuntimeError):
    """Raised in strict mode when Expedition is not running, so a write would be dropped."""


class ExpeditionWriteError(RuntimeError):
    """Raised in strict mode when a value written to Expedition does not read back."""


class ExpeditionProtocolError(ValueError):
    """Raised when simple-protocol text is malformed, or a command argument is invalid.

    It is a ValueError, so callers that already catch bad input need no change.
    """


class ExpeditionWriteWarning(UserWarning):
    """Warns that Expedition is likely to ignore a write, e.g. a GPS channel on boat 0."""


class ExpeditionVersionWarning(UserWarning):
    """Warns that the installed Expedition does not match what this package expects."""
