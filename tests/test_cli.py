import os
import unicodedata

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


@pytest.mark.parametrize("command", [["render", "intro.txt"], ["voices"]])
@pytest.mark.parametrize("args", [["--pitch=-8Hz"], ["--pitch", "-8Hz"]])
def test_pitch_accepts_leading_minus_in_both_forms(command, args):
    assert cli.build_parser().parse_args([*command, *args]).pitch == "-8Hz"


def test_render_defaults():
    a = cli.build_parser().parse_args(["render", "intro.txt"])
    assert (a.voice, a.rate, a.pitch, a.wrap, a.whisper_model, a.title) == (
        "pl-PL-ZofiaNeural", "-10%", None, 54, "medium", "MU/TH/UR 6000 :: USCSS MONTERO")


def test_render_passes_pitch_to_tts(script, monkeypatch, rendered):
    pitches = []

    def fake_tts(text, voice, rate, workdir, pitch=None):
        pitches.append(pitch)
        mp3 = os.path.join(workdir, "narration.mp3")
        open(mp3, "wb").close()
        return mp3, [[0.0, 1.0, text]]

    monkeypatch.setattr(cli.narration, "run_tts", fake_tts)
    cli.main(["render", str(script), "--pitch=-8Hz"])
    assert pitches == ["-8Hz"]


def test_tts_mode_saves_narration_next_to_video(script, monkeypatch, rendered):
    def fake_tts(source, voice, rate, workdir, pitch=None):
        mp3 = os.path.join(workdir, "narration.mp3")
        with open(mp3, "wb") as f:
            f.write(b"mp3")
        return mp3, [[0.0, 1.0, "Raport systemowy."]]

    monkeypatch.setattr(cli.narration, "run_tts", fake_tts)
    cli.main(["render", str(script)])
    assert (script.parent / "intro_lektor.mp3").read_bytes() == b"mp3"
    cues, _audio, out, image, font, wrap, upper, hum, title, fx = rendered[0]
    assert cues == [[0.0, 1.0, "Raport systemowy."]]
    assert out == str(script.parent / "intro.mp4")
    assert (image, font, wrap, upper, hum, fx) == (None, None, 54, True, True, "echo")


def test_own_audio_alignment_writes_editable_srt(script, tmp_path, monkeypatch, rendered):
    monkeypatch.setattr(cli.align, "align_cues", lambda text, audio, size: [[0.5, 1.5, "Raport systemowy."]])
    cli.main(["render", str(script), "--audio", "voice.mp3", "-o", str(tmp_path / "film.mp4")])
    assert "00:00:00,500 --> 00:00:01,500" in (tmp_path / "film_napisy.srt").read_text(encoding="utf-8")
    assert rendered[0][1] == "voice.mp3"


def test_own_audio_gets_the_chosen_voice_fx(script, monkeypatch, rendered):
    cli.main(["render", str(script), "--audio", "voice.mp3", "--no-align", "--voice-fx", "intercom"])
    assert rendered[0][-1] == "intercom"


def test_render_rejects_unknown_voice_fx(capsys):
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["render", "intro.txt", "--voice-fx", "reverb"])


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



def test_decomposed_bom_script_reaches_tts_and_screen_composed(tmp_path, monkeypatch, rendered):
    path = tmp_path / "intro.txt"
    path.write_bytes(b"\xef\xbb\xbf" + unicodedata.normalize("NFD", "Matka was obudziła.\n").encode("utf-8"))
    spoken = []

    def fake_tts(text, voice, rate, workdir, pitch=None):
        spoken.append(text)
        mp3 = os.path.join(workdir, "narration.mp3")
        open(mp3, "wb").close()
        return mp3, [[0.0, 1.0, text]]

    monkeypatch.setattr(cli.narration, "run_tts", fake_tts)
    cli.main(["render", str(path)])
    assert spoken == ["Matka was obudziła."]
    assert rendered[0][0] == [[0.0, 1.0, "Matka was obudziła."]]

@pytest.fixture
def auditioned(monkeypatch):
    calls = []

    def fake_audition(voices, text, rate, outdir, player=None, pitch=None, fx=None):
        calls.append({"voices": voices, "text": text, "rate": rate, "outdir": outdir, "player": player,
                      "pitch": pitch, "fx": fx})
        return [(v, os.path.join(outdir, f"{v}.mp3")) for v in voices]

    monkeypatch.setattr(cli.narration, "audition", fake_audition)
    return calls


def test_voices_defaults(monkeypatch, auditioned):
    monkeypatch.setattr(cli.narration, "find_player", lambda: print)
    cli.main(["voices"])
    (call,) = auditioned
    assert call["voices"] == cli.narration.DEFAULT_VOICES
    assert (call["text"], call["rate"], call["pitch"], call["player"]) == (
        cli.narration.SAMPLE, "-10%", None, print)


def test_voices_without_voice_fx_plays_dry_samples(monkeypatch, auditioned):
    monkeypatch.setattr(cli.narration, "find_player", lambda: print)
    cli.main(["voices"])
    assert auditioned[0]["fx"] is None


def test_voices_runs_samples_through_the_chosen_fx(monkeypatch, auditioned):
    applied = []
    monkeypatch.setattr(cli.narration, "find_player", lambda: print)
    monkeypatch.setattr(cli.mux, "apply_fx", lambda src, dst, fx: applied.append((src, dst, fx)) or True)
    cli.main(["voices", "--voice-fx", "intercom"])
    assert auditioned[0]["fx"]("a.mp3", "a_fx.mp3")
    assert applied == [("a.mp3", "a_fx.mp3", "intercom")]


def test_voices_passes_pitch(monkeypatch, auditioned):
    monkeypatch.setattr(cli.narration, "find_player", lambda: print)
    cli.main(["voices", "--voice", "pl-PL-ZofiaNeural", "--rate=-15%", "--pitch=-8Hz"])
    assert auditioned[0]["pitch"] == "-8Hz"


def test_voices_repeatable_voice_and_equals_rate(monkeypatch, auditioned):
    monkeypatch.setattr(cli.narration, "find_player", lambda: print)
    cli.main(["voices", "--voice", "pl-PL-MarekNeural", "--voice", "de-DE-SeraphinaMultilingualNeural",
              "--rate=-15%", "--text", "Matka was obudziła."])
    assert auditioned[0]["voices"] == ["pl-PL-MarekNeural", "de-DE-SeraphinaMultilingualNeural"]
    assert auditioned[0]["rate"] == "-15%"


def test_voices_without_afplay_saves_samples(tmp_path, monkeypatch, auditioned):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli.narration, "find_player", lambda: None)
    cli.main(["voices"])
    assert auditioned[0]["outdir"] == "audition"
    assert auditioned[0]["player"] is None
    assert (tmp_path / "audition").is_dir()


def test_voices_fails_when_nothing_synthesised(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli.narration, "find_player", lambda: None)
    monkeypatch.setattr(cli.narration, "audition", lambda *a, **k: [])
    with pytest.raises(SystemExit, match="no voice"):
        cli.main(["voices", "--no-play"])
