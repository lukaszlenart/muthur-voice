from pathlib import Path

import pytest
from PIL import Image

from muthur import boot, cli
from muthur.render import H, W
from muthur.text import read_text, split_sentences

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
NAMES = ["wake-up", "corridor", "orbit", "signal", "cold-start"]


def test_every_example_folder_is_listed():
    assert sorted(p.name for p in EXAMPLES.iterdir() if p.is_dir()) == sorted(NAMES)


@pytest.mark.parametrize("name", NAMES)
def test_example_config_loads_and_its_files_exist(name, capsys):
    folder = EXAMPLES / name
    a = cli.parse_args(["render", str(folder / "intro.txt"), "--config", str(folder / "muthur.toml")],
                       check_files=True)
    assert a.image == str(folder / "background.jpg")


@pytest.mark.parametrize("name", NAMES)
def test_example_background_is_full_hd(name):
    with Image.open(EXAMPLES / name / "background.jpg") as img:
        assert img.size == (W, H)


@pytest.mark.parametrize("name", NAMES)
def test_example_intro_is_polish_sentences(name):
    _, narrated = boot.split_boot(read_text(EXAMPLES / name / "intro.txt"))
    sentences = split_sentences(narrated)
    assert 6 <= len(sentences) <= 20
    assert any(c in "ąćęłńóśźż" for c in "".join(sentences).lower())


def test_cold_start_shows_every_boot_tag():
    steps, _ = boot.split_boot(read_text(EXAMPLES / "cold-start" / "intro.txt"))
    assert {s.kind for s in steps} == {"line", "blank", "bar", "status", "count"}


@pytest.mark.parametrize("name", NAMES)
def test_example_boot_block_fits_its_wrap(name, capsys):
    folder = EXAMPLES / name
    a = cli.parse_args(["render", str(folder / "intro.txt"), "--config", str(folder / "muthur.toml")])
    steps, _ = boot.split_boot(read_text(folder / "intro.txt"))
    boot.plan(steps, boot.Timing(a.boot_type_speed), a.wrap, a.upper)
