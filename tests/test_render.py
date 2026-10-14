import hashlib
import json

import pytest
from PIL import Image, ImageDraw

from golden.harness import FIXTURES, golden_path, requires_menlo
from muthur.render import build_blocks, iter_frames, load_font, timeline
from muthur.timing import estimate_cues

POLISH = "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ"
BASE = "acelnoszzACELNOSZZ"


def test_upper_casing_and_wrapping_keep_polish_letters():
    assert build_blocks([[0, 1, "zażółć gęślą jaźń zażółć"]], 12, True) == [
        (0, 1, ["ZAŻÓŁĆ GĘŚLĄ", "JAŹŃ ZAŻÓŁĆ"])]


def test_no_upper_keeps_original_case():
    assert build_blocks([[0, 1, "Matka was obudziła"]], 54, False) == [(0, 1, ["Matka was obudziła"])]


def test_empty_cue_text_still_yields_one_line():
    assert build_blocks([[0, 1, ""]], 54, True) == [(0, 1, [""])]


def _glyph(font, ch):
    im = Image.new("L", (80, 80))
    ImageDraw.Draw(im).text((10, 10), ch, font=font, fill=255)
    return im.tobytes()


@requires_menlo
@pytest.mark.parametrize("ch,base", list(zip(POLISH, BASE)))
def test_default_font_draws_polish_diacritics(ch, base):
    font = load_font(46)
    assert _glyph(font, ch) != _glyph(font, "\u0378")  # unassigned code point -> missing-glyph box
    assert _glyph(font, ch) != _glyph(font, base)


def test_missing_font_path_falls_back_to_system_font():
    assert load_font(46, "/nonexistent/font.ttf").size == 46


def test_timeline_adds_lead_in_and_tail():
    assert timeline([[0.0, 1.0, "a"]]) == ([[2.0, 3.0, "a"]], 6.0)
    assert timeline([]) == ([], 8.0)


@requires_menlo
@pytest.mark.golden
def test_preview_frames_match_prototype():
    expected = json.loads(golden_path("preview").read_text(encoding="utf-8"))
    raw = (FIXTURES / "short.txt").read_text(encoding="utf-8").strip()
    total, frames = iter_frames(estimate_cues(raw), None, None, 54, True, "MU/TH/UR 6000 :: USCSS MONTERO")
    assert [hashlib.sha256(data).hexdigest() for _, data in frames] == expected["frames"]
