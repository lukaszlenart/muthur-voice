import os

import pytest

from muthur import cli
from muthur.timing import estimate_cues


@pytest.fixture
def rendered(monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "render_video", lambda *args: calls.append(args))
    return calls


@pytest.fixture
def script(tmp_path):
    path = tmp_path / "intro.txt"
    path.write_text("Raport systemowy. Witamy z powrotem, załogo.\n", encoding="utf-8")
    return path


@pytest.mark.parametrize("args", [["--rate=-15%"], ["--rate", "-15%"]])
def test_rate_accepts_leading_minus_in_both_forms(args):
    assert cli.build_parser().parse_args(["render", "intro.txt", *args]).rate == "-15%"


def test_render_defaults_match_prototype():
    a = cli.build_parser().parse_args(["render", "intro.txt"])
    assert (a.voice, a.rate, a.wrap, a.whisper_model, a.title) == (
        "pl-PL-ZofiaNeural", "-10%", 54, "small", "MU/TH/UR 6000 :: USCSS MONTERO")


def test_tts_mode_saves_narration_next_to_video(script, monkeypatch, rendered):
    def fake_tts(source, voice, rate, workdir):
        mp3 = os.path.join(workdir, "narration.mp3")
        with open(mp3, "wb") as f:
            f.write(b"mp3")
        return mp3, [[0.0, 1.0, "Raport systemowy."]]

    monkeypatch.setattr(cli.narration, "run_tts", fake_tts)
    cli.main(["render", str(script)])
    assert (script.parent / "intro_lektor.mp3").read_bytes() == b"mp3"
    cues, _audio, out, image, font, wrap, upper, hum, title = rendered[0]
    assert cues == [[0.0, 1.0, "Raport systemowy."]]
    assert out == str(script.parent / "intro.mp4")
    assert (image, font, wrap, upper, hum) == (None, None, 54, True, True)


def test_own_audio_alignment_writes_editable_srt(script, tmp_path, monkeypatch, rendered):
    monkeypatch.setattr(cli.align, "align_cues", lambda text, audio, size: [[0.5, 1.5, "Raport systemowy."]])
    cli.main(["render", str(script), "--audio", "voice.mp3", "-o", str(tmp_path / "film.mp4")])
    assert "00:00:00,500 --> 00:00:01,500" in (tmp_path / "film_napisy.srt").read_text(encoding="utf-8")
    assert rendered[0][1] == "voice.mp3"


def test_own_audio_without_whisper_estimates_timing(script, tmp_path, monkeypatch, rendered):
    monkeypatch.setattr(cli.align, "align_cues", lambda *a: None)
    cli.main(["render", str(script), "--audio", "voice.mp3"])
    assert rendered[0][0] == estimate_cues("Raport systemowy. Witamy z powrotem, załogo.")
    assert not (tmp_path / "intro_napisy.srt").exists()


def test_no_align_never_calls_whisper(script, monkeypatch, rendered):
    def boom(*a):
        raise AssertionError("Whisper must not run with --no-align")
    monkeypatch.setattr(cli.align, "align_cues", boom)
    cli.main(["render", str(script), "--audio", "voice.mp3", "--no-align"])
    assert rendered
