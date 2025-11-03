"""Compatibility package for legacy imports from `modules`.

Many implementations live under `client_code/` in this repository. Older
entry points (including tests and `streamlit_app.py`) import using the
`modules.*` namespace. To keep backward compatibility we import the
corresponding module from `client_code` and register it under the
`modules` package namespace so both `from modules import foo` and
`from modules.foo import X` continue to work.

This file intentionally performs a light-weight import of the matching
modules in `client_code/`. If any import fails we silently skip it so
tests for unrelated modules can still run.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

__all__: list[str] = []

_client_pkg = "client_code"
_client_dir = Path(__file__).resolve().parent.parent / _client_pkg

# build exports in a temporary list to avoid mutating __all__ dynamically
_exports: list[str] = []

if _client_dir.exists():
	for p in _client_dir.glob("*.py"):
		name = p.stem
		# skip private and package files
		if name.startswith("_"):
			continue
		try:
			mod = importlib.import_module(f"{_client_pkg}.{name}")
			# make the module available as `modules.<name>`
			sys.modules[f"{__name__}.{name}"] = mod
			globals()[name] = mod
			_exports.append(name)
		except Exception:
			# skip modules that fail to import (tests will surface real errors)
			continue

# assign the finalized export list to __all__
# Note: some static analyzers (e.g. Pyright/Pylance) don't support dynamic modifications
# of __all__; add a type-ignore comment to suppress false positives while preserving
# runtime behavior.
__all__ = _exports  # type: ignore

