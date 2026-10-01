"""Repository test package and compatibility alias for legacy test imports."""

import sys

try:
    from . import test_pipeline as _test_pipeline
except ImportError:
    _test_pipeline = None
else:
    sys.modules.setdefault("test_pipeline", _test_pipeline)
