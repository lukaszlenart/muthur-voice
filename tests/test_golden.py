import json

import pytest

from golden.harness import SCENARIOS, golden_path, require_raqm, requires_menlo, run_scenario
from muthur.cli import main

pytestmark = [pytest.mark.golden, requires_menlo]


@pytest.mark.parametrize("name", SCENARIOS)
def test_render_matches_prototype(name, tmp_path):
    require_raqm()
    expected = json.loads(golden_path(name).read_text(encoding="utf-8"))
    actual = run_scenario(name, lambda args: main(["render", *args]), tmp_path)
    assert actual["cmd"] == expected["cmd"]
    assert len(actual["frames"]) == len(expected["frames"])
    first_diff = next((i for i, (a, b) in enumerate(zip(actual["frames"], expected["frames"])) if a != b), None)
    assert first_diff is None, f"frame {first_diff} differs from the prototype"
