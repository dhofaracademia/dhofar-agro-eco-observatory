"""Execute every acceptance script, including standalone main-based tests."""
import subprocess
import sys
from pathlib import Path
for path in sorted(Path(__file__).parent.glob('test_*.py')):
    print(f'Running {path.name}', flush=True)
    subprocess.run([sys.executable, str(path)], check=True)
