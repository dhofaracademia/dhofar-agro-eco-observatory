import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engines.data_quality import data_quality_confidence, MIN_VALID_PIXELS
from engines.observation_integrity import DEFAULT_MIN_CLEAR_PIXELS_CELL
from engines.stress import map_stress_to_alert

def main():
    assert MIN_VALID_PIXELS == DEFAULT_MIN_CLEAR_PIXELS_CELL
    for pixels in (None, 0, 1, 49, -1, float('nan'), float('inf')):
        assert data_quality_confidence(0, pixels) == 0
    for pixels in (1, 49, 50, 100, 500):
        dq = data_quality_confidence(0, pixels)
        alert = map_stress_to_alert(ndvi=.7, bare_floor=.18, water={'water_stress_score':0}, vigor={'vigor_stress_score':0}, data_quality_confidence=dq)
        assert alert == 'unclear', (pixels, dq, alert)
    assert data_quality_confidence(None, 2500) == 0
    assert data_quality_confidence(0, 50) == 2
    assert data_quality_confidence(0, 2500) == 97
    print('PASS coverage guard and downstream alert regression')
if __name__ == '__main__': main()
