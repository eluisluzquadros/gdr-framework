"""
Utils package for GDR Framework
"""

from .safe_print import (
    safe_string,
    safe_print,
    safe_log,
    SafeLogger,
    setup_safe_logging,
    UNICODE_REPLACEMENTS
)

__all__ = [
    'safe_string',
    'safe_print',
    'safe_log',
    'SafeLogger',
    'setup_safe_logging',
    'UNICODE_REPLACEMENTS'
]