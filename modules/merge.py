"""Compatibility wrapper for merge functionality.

The main implementation lives in `client_code.merge`. This wrapper simply
re-exports the `merge_files` symbol so existing imports that use
`from modules.merge import merge_files` continue to work.
"""
from client_code.merge import merge_files  # re-export implementation

__all__ = ["merge_files"]
