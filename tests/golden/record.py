"""Re-record golden frame hashes after an intended look change: uv run python tests/golden/record.py"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from golden.harness import SCENARIOS, golden_path, run_scenario  # noqa: E402
from muthur.cli import main  # noqa: E402

for name in SCENARIOS:
    with tempfile.TemporaryDirectory() as tmp:
        result = run_scenario(name, lambda args: main(["render", *args]), Path(tmp))
    golden_path(name).write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(f"{name}: {len(result['frames'])} frames")
