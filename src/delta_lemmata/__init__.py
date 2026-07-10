"""Delta's Python package boundary.

The analysis engine is R stylo. Python owns orchestration, validation, and the
browser application around that engine.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("delta-lemmata")
except PackageNotFoundError:  # pragma: no cover - only an uninstalled source tree
    __version__ = "0+uninstalled"

__all__ = ["__version__"]
