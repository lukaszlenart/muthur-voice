import os
import unicodedata

import pytest

from muthur import cli
from muthur.timing import estimate_cues


@pytest.fixture(autouse=True)
def without_config_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def voice(tmp_path):
    (tmp_path / "voice.mp3").write_bytes(b"")
    return "voice.mp3"


@pytest.fixture
def rendered(monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "render_video", lambda *args, **kwargs: calls.append(args))
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
        "pl-PL-ZofiaNeural", "-20%", "-24Hz", 54, "medium", "MU/TH/UR 6000 :: USCSS MONTERO")


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
    assert (image, font, wrap, upper, hum, fx) == (None, None, 54, True, True, "intercom")


def test_own_audio_alignment_writes_editable_srt(script, tmp_path, monkeypatch, rendered, voice):
    monkeypatch.setattr(cli.align, "align_cues", lambda text, audio, size: [[0.5, 1.5, "Raport systemowy."]])
    cli.main(["render", str(script), "--audio", "voice.mp3", "-o", str(tmp_path / "film.mp4")])
    assert "00:00:00,500 --> 00:00:01,500" in (tmp_path / "film_napisy.srt").read_text(encoding="utf-8")
    assert rendered[0][1] == "voice.mp3"


def test_own_audio_gets_the_chosen_voice_fx(script, monkeypatch, rendered, voice):
    cli.main(["render", str(script), "--audio", "voice.mp3", "--no-align", "--voice-fx", "intercom"])
    assert rendered[0][-1] == "intercom"


def test_render_rejects_unknown_voice_fx(capsys):
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["render", "intro.txt", "--voice-fx", "reverb"])


def test_srt_without_audio_is_rejected_before_tts(script, monkeypatch, capsys):
    def boom(*a, **k):
        raise AssertionError("edge-tts must not run when --srt is rejected")
    monkeypatch.setattr(cli.narration, "run_tts", boom)
    with pytest.raises(SystemExit) as e:
        cli.main(["render", str(script), "--srt", "intro_napisy.srt"])
    assert e.value.code == 2
    assert "--srt needs --audio" in capsys.readouterr().err


def test_no_align_without_audio_is_rejected_before_tts(script, monkeypatch, capsys):
    def boom(*a, **k):
        raise AssertionError("edge-tts must not run when --no-align is rejected")
    monkeypatch.setattr(cli.narration, "run_tts", boom)
    with pytest.raises(SystemExit) as e:
        cli.main(["render", str(script), "--no-align"])
    assert e.value.code == 2
    assert "--no-align needs --audio" in capsys.readouterr().err


def test_own_audio_without_whisper_estimates_timing(script, tmp_path, monkeypatch, rendered, voice):
    monkeypatch.setattr(cli.align, "align_cues", lambda *a: None)
    cli.main(["render", str(script), "--audio", "voice.mp3"])
    assert rendered[0][0] == estimate_cues("Raport systemowy. Witamy z powrotem, załogo.")
    assert not (tmp_path / "intro_napisy.srt").exists()


def test_no_align_never_calls_whisper(script, monkeypatch, rendered, voice):
    def boom(*a):
        raise AssertionError("Whisper must not run with --no-align")
    monkeypatch.setattr(cli.align, "align_cues", boom)
    cli.main(["render", str(script), "--audio", "voice.mp3", "--no-align"])
    assert rendered


def no_tts(*a, **k):
    raise AssertionError("edge-tts must not run when an input file is missing")


@pytest.mark.parametrize("flag", ["--image", "--font", "--audio"])
def test_missing_input_file_is_rejected_before_tts(script, monkeypatch, capsys, flag):
    monkeypatch.setattr(cli.narration, "run_tts", no_tts)
    with pytest.raises(SystemExit) as e:
        cli.main(["render", str(script), flag, "brak.jpg"])
    assert e.value.code == 2
    assert f"{flag} not found: brak.jpg" in capsys.readouterr().err


def test_missing_srt_is_rejected(script, monkeypatch, capsys, voice):
    with pytest.raises(SystemExit):
        cli.main(["render", str(script), "--audio", voice, "--srt", "brak.srt"])
    assert "--srt not found: brak.srt" in capsys.readouterr().err


def test_missing_text_file_is_rejected(capsys):
    with pytest.raises(SystemExit):
        cli.main(["render", "brak.txt"])
    assert "text not found: brak.txt" in capsys.readouterr().err


def test_missing_file_from_config_names_the_config(script, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli.narration, "run_tts", no_tts)
    (tmp_path / "muthur.toml").write_text('[render]\nimage = "montero.jpg"\n', encoding="utf-8")
    with pytest.raises(SystemExit):
        cli.main(["render", str(script)])
    assert f"image in muthur.toml not found: {tmp_path / 'montero.jpg'}" in capsys.readouterr().err


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
        cli.narration.SAMPLE, "-20%", "-24Hz", print)


def test_voices_with_voice_fx_none_plays_dry_samples(monkeypatch, auditioned):
    monkeypatch.setattr(cli.narration, "find_player", lambda: print)
    cli.main(["voices", "--voice-fx", "none"])
    assert auditioned[0]["fx"] is None


def test_voices_default_to_the_render_voice_fx(monkeypatch, auditioned):
    applied = []
    monkeypatch.setattr(cli.narration, "find_player", lambda: print)
    monkeypatch.setattr(cli.mux, "apply_fx", lambda src, dst, fx: applied.append(fx) or True)
    cli.main(["voices"])
    auditioned[0]["fx"]("a.mp3", "a_fx.mp3")
    assert applied == ["intercom"]


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


BOOTED = "[BOOT start]\n[Status: AKTYWNE, text: ŻYCIE]\n[BOOT end]\nRaport systemowy.\n"


def test_tts_gets_only_the_narrated_text(tmp_path, monkeypatch):
    path = tmp_path / "intro.txt"
    path.write_text(BOOTED, encoding="utf-8")
    texts = []

    def fake_tts(text, voice, rate, workdir, pitch=None):
        texts.append(text)
        mp3 = os.path.join(workdir, "narration.mp3")
        open(mp3, "wb").close()
        return mp3, [[0.0, 1.0, text]]

    screens = []
    monkeypatch.setattr(cli.narration, "run_tts", fake_tts)
    monkeypatch.setattr(cli, "render_video", lambda *args, boot_screen, clicks: screens.append(boot_screen))
    cli.main(["render", str(path)])
    assert texts == ["Raport systemowy."]
    assert screens[0].duration > 0


def test_boot_shifts_voice_and_cues_by_the_same_amount(tmp_path, monkeypatch, voice):
    path = tmp_path / "intro.txt"
    path.write_text(BOOTED, encoding="utf-8")
    (tmp_path / "s.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nRaport systemowy.\n", encoding="utf-8")
    seen = {}

    def fake_frames(cues, *args, boot=None):
        seen["shift"] = boot.duration
        return 10.0, iter(())

    monkeypatch.setattr(cli.render, "iter_frames", fake_frames)
    monkeypatch.setattr(cli.mux, "encode", lambda frames, total, cmd, out: seen.setdefault("cmd", cmd))
    cli.main(["render", str(path), "--audio", voice, "--srt", "s.srt", "--no-boot-clicks"])
    ms = int((seen["shift"] + cli.render.LEAD_IN) * 1000)
    assert f"adelay={ms}|{ms}" in seen["cmd"][seen["cmd"].index("-filter_complex") + 1]


def test_boot_flag_defaults():
    a = cli.build_parser().parse_args(["render", "intro.txt"])
    assert (a.boot_type_speed, a.boot_status_pause, a.boot_bar_time, a.boot_count_time, a.boot_hold,
            a.boot_clicks) == (22.0, 0.7, 1.5, 2.0, 2.0, True)


@pytest.mark.parametrize("args", [["--boot-type-speed", "0"], ["--boot-hold", "-1"]])
def test_non_positive_type_speed_is_rejected(args, capsys):
    with pytest.raises(SystemExit):
        cli.parse_args(["render", "intro.txt", *args])
    assert f"{args[0]} must be" in capsys.readouterr().err


def test_boot_errors_count_leading_blank_lines(tmp_path, capsys):
    path = tmp_path / "intro.txt"
    path.write_bytes("﻿\r\n\r\n[BOOT start]\r\nA\r\n[ProgresBar: 1..2, text: R]\r\n[BOOT end]\r\nB.\r\n".encode())
    with pytest.raises(SystemExit, match=r"^line 5: unknown tag ProgresBar"):
        cli.main(["render", str(path), "--no-tts"])


def test_boot_starts_typing_after_the_power_on_fade(tmp_path, monkeypatch):
    path = tmp_path / "intro.txt"
    path.write_text(BOOTED, encoding="utf-8")
    screens = []
    monkeypatch.setattr(cli, "render_video", lambda *args, boot_screen, clicks: screens.append(boot_screen))
    cli.main(["render", str(path), "--no-tts"])
    assert screens[0].clicks[0] == pytest.approx(cli.render.POWER_ON)
