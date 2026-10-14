"""Record golden frame hashes: uv run python tests/golden/record.py prototype|package"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]

from golden.harness import SCENARIOS, golden_path, run_scenario  # noqa: E402


def prototype_main(args):
    import mother_intro
    sys.argv = ["mother_intro.py", *args]
    mother_intro.main()


def package_main(args):
    from muthur.cli import main
    main(["render", *args])


target = {"prototype": prototype_main, "package": package_main}[sys.argv[1]]
for name in SCENARIOS:
    with tempfile.TemporaryDirectory() as tmp:
        result = run_scenario(name, target, Path(tmp))
    golden_path(name).write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(f"{name}: {len(result['frames'])} frames")
