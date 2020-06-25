from gdacclient import GdacClient

__all__ = [
    "GdacClient",
]

try:
    from ._version import __version__
except ImportError:
    __version__ = "unknown"
