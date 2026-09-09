"""NDRE — SCIENCE_LOCKS Phase 1 / AgriTech STAC prefs.

Primary: NDRE = (B08 - B05) / (B08 + B05)
Documented fallback only: B06 or B07 if B05 missing (schema README).
No silent third formula. If no red-edge band → ndre=None, ndre_available=False.
SCL gates must already have been applied before calling compute_ndre.
"""

from __future__ import annotations

from typing import Any

import numpy as np

SCALE = 10000.0


def ndre_status_from_band(band_used: str | None) -> dict[str, Any]:
    if band_used == "B05":
        return {"ndre_available": True, "ndre_band": "B05", "ndre_status": "ok"}
    if band_used in ("B06", "B07"):
        return {
            "ndre_available": True,
            "ndre_band": band_used,
            "ndre_status": f"fallback_{band_used}",
        }
    return {
        "ndre_available": False,
        "ndre_band": None,
        "ndre_status": "unavailable",
    }


def compute_ndre(
    b08: np.ndarray,
    *,
    b05: np.ndarray | None = None,
    b06: np.ndarray | None = None,
    b07: np.ndarray | None = None,
    valid: np.ndarray | None = None,
    scale: float = SCALE,
) -> tuple[np.ndarray | None, str | None, dict[str, Any]]:
    """Return (ndre_array_or_None, band_used, status_dict).

    Preference order: B05 → B06 → B07 (documented fallback only).
    """
    band = None
    red_edge = None
    if b05 is not None:
        band, red_edge = "B05", b05
    elif b06 is not None:
        band, red_edge = "B06", b06
    elif b07 is not None:
        band, red_edge = "B07", b07

    status = ndre_status_from_band(band)
    if band is None or red_edge is None:
        return None, None, status

    nir = b08.astype(np.float32) / scale
    re = red_edge.astype(np.float32) / scale
    ndre = np.full(b08.shape, np.nan, dtype=np.float32)
    denom = nir + re
    ok = (np.abs(denom) > 1e-6) & np.isfinite(denom)
    if valid is not None:
        ok = ok & valid
    # reflectance sanity (raw DN before scale already gated by caller often)
    ok = ok & (b08 > 0) & (red_edge > 0)
    ndre[ok] = (nir[ok] - re[ok]) / denom[ok]
    return ndre, band, status
