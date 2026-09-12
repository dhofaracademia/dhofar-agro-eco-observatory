#!/usr/bin/env python3
"""Regenerate Phase-4 seed artifacts from SCIENCE_LOCKS scaffold."""
from __future__ import annotations
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from engines.seed_intelligence import OUT_DIR, build_catalog, DISCLAIMER_EN

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    catalog = build_catalog()
    (OUT_DIR / "species_catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("wrote", OUT_DIR / "species_catalog.json", "n=", len(catalog["species"]))
    print("disclaimer:", DISCLAIMER_EN)

if __name__ == "__main__":
    main()
