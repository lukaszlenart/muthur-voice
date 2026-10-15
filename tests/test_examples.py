from pathlib import Path

import pytest
from PIL import Image

from muthur import cli
from muthur.render import H, W
from muthur.text import read_text, split_sentences

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
NAMES = ["wake-up", "corridor", "orbit", "signal"]


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
    sentences = split_sentences(read_text(EXAMPLES / name / "intro.txt"))
    assert 6 <= len(sentences) <= 20
    assert any(c in "ąćęłńóśźż" for c in "".join(sentences).lower())
