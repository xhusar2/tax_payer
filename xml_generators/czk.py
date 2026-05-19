"""CZK amount helpers for DPH / KH XML (whole koruny)."""

from __future__ import annotations

import math


def czk_round(amount: float) -> int:
    """Whole CZK, standard rounding (bases / obrat)."""
    return int(round(amount))


def czk_ceil_tax(amount: float) -> int:
    """Whole CZK, rounded up (daň / odpočet lines)."""
    if amount <= 0:
        return 0
    return math.ceil(amount - 1e-9)
