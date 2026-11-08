"""Repository test package.

Several suites import the shared fixtures as a top-level ``test_pipeline``
module. Declaring ``tests`` as a package makes pytest import test modules as
``tests.*``, so the legacy top-level name is registered here — once, and
without hiding an import failure behind a silent fallback.
"""

import sys

from . import test_pipeline

sys.modules.setdefault("test_pipeline", test_pipeline)
