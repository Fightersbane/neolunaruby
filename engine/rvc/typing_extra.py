"""Type definitions for the vendored RVC inference code.

Minimal replacement for ultimate_rvc.typing_extra. Only rmvpe is actually
implemented in this slim build (see engine/rvc/lib/predictors/f0.py); the
other enum members are kept so convert_audio's signature stays intact.
"""

from __future__ import annotations

from enum import StrEnum


class F0Method(StrEnum):
    """Enumeration of pitch extraction methods."""

    RMVPE = "rmvpe"
    CREPE = "crepe"
    CREPE_TINY = "crepe-tiny"
    FCPE = "fcpe"
