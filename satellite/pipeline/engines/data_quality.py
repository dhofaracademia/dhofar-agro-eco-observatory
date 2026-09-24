"""Coverage-capped heuristic. No diagnostic accuracy or calibration claim."""
import json
import math
from pathlib import Path

POLICY = json.loads((Path(__file__).resolve().parents[3] / 'app/src/data/qualityPolicy.json').read_text())
MIN_VALID_PIXELS = POLICY['min_valid_pixels']

def data_quality_confidence(cloud_cover: float | None, pixel_count: int | None) -> float:
    if isinstance(pixel_count, bool) or not isinstance(pixel_count, (int, float)) or not math.isfinite(pixel_count):
        return 0.0
    if pixel_count != int(pixel_count) or pixel_count < MIN_VALID_PIXELS:
        return 0.0
    if isinstance(cloud_cover, bool) or not isinstance(cloud_cover, (int, float)) or not math.isfinite(cloud_cover) or not 0 <= cloud_cover <= 100:
        return 0.0
    fraction = min(1.0, pixel_count / POLICY['expected_pixels'])
    if fraction < POLICY['min_valid_fraction']:
        return 0.0
    weighted = POLICY['scene_weight'] * max(0.0, 100 - cloud_cover * POLICY['cloud_penalty']) + POLICY['pixel_weight'] * fraction * 100
    # Same positive-number rounding as the frontend; cap cannot exceed observed %.
    return math.floor(min(POLICY['max_score'], weighted, fraction * 100) * 10 + 0.5) / 10
