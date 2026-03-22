"""killpy detector package.

All concrete detectors are exported here.  :data:`ALL_DETECTORS` provides
the canonical ordered list used by :class:`~killpy.scanner.Scanner` when no
explicit detector selection is given.
"""

from __future__ import annotations

from killpy.detectors.artifacts import ArtifactsDetector
from killpy.detectors.base import AbstractDetector
from killpy.detectors.cache import CacheDetector
from killpy.detectors.conda import CondaDetector
from killpy.detectors.hatch import HatchDetector
from killpy.detectors.pipenv import PipenvDetector
from killpy.detectors.pipx import PipxDetector
from killpy.detectors.poetry import PoetryDetector
from killpy.detectors.pyenv import PyenvDetector
from killpy.detectors.tox import ToxDetector
from killpy.detectors.uv import UvDetector
from killpy.detectors.venv import VenvDetector

__all__ = [
    "AbstractDetector",
    "ArtifactsDetector",
    "CacheDetector",
    "CondaDetector",
    "HatchDetector",
    "PyenvDetector",
    "PipenvDetector",
    "PipxDetector",
    "PoetryDetector",
    "ToxDetector",
    "UvDetector",
    "VenvDetector",
    "ALL_DETECTORS",
]

# Ordered list of all detector classes.  The Scanner instantiates these in
# this order; it respects ``can_handle()`` before calling ``detect()``.
ALL_DETECTORS: list[type[AbstractDetector]] = [
    VenvDetector,
    PoetryDetector,
    CondaDetector,
    PipxDetector,
    PyenvDetector,
    PipenvDetector,
    HatchDetector,
    UvDetector,
    ToxDetector,
    CacheDetector,
    ArtifactsDetector,
]
