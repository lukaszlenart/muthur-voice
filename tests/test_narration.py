from pathlib import Path

from muthur import narration


def test_edge_tts_cmd_for_a_file_matches_prototype():
    assert narration.edge_tts_cmd("pl-PL-ZofiaNeural", "-10%", "n.mp3", file="intro.txt", srt="n.srt") == [
        "edge-tts", "--voice", "pl-PL-ZofiaNeural", "--rate=-10%", "--file", "intro.txt",
        "--write-media", "n.mp3", "--write-subtitles", "n.srt"]


def test_edge_tts_cmd_for_inline_text_survives_leading_dash():
    assert narration.edge_tts_cmd("pl-PL-MarekNeural", "+0%", "s.mp3", text="-- Raport.") == [
        "edge-tts", "--voice", "pl-PL-MarekNeural", "--rate=+0%", "--text=-- Raport.", "--write-media", "s.mp3"]


def test_edge_tts_cmd_puts_pitch_after_rate():
    assert narration.edge_tts_cmd("pl-PL-ZofiaNeural", "-15%", "s.mp3", pitch="-8Hz", text="Raport.") == [
        "edge-tts", "--voice", "pl-PL-ZofiaNeural", "--rate=-15%", "--pitch=-8Hz", "--text=Raport.",
        "--write-media", "s.mp3"]


def test_run_tts_passes_pitch(tmp_path, monkeypatch):
    seen = []

    def fake_run(cmd, check):
        seen.append(cmd)
        Path(cmd[cmd.index("--write-subtitles") + 1]).write_text("", encoding="utf-8")

    monkeypatch.setattr(narration.subprocess, "run", fake_run)
    narration.run_tts("Raport.", "pl-PL-ZofiaNeural", "-15%", str(tmp_path), pitch="-8Hz")
    assert "--pitch=-8Hz" in seen[0]


def test_synthesize_passes_pitch(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(narration.shutil, "which", lambda name: "/usr/bin/edge-tts")
    monkeypatch.setattr(narration.subprocess, "run",
                        lambda cmd: seen.append(cmd) or narration.subprocess.CompletedProcess(cmd, 0))
    assert narration.synthesize("pl-PL-MarekNeural", "-15%", "Raport.", "s.mp3", pitch="-15Hz")
    assert "--pitch=-15Hz" in seen[0]


def test_run_tts_reads_the_given_text(tmp_path, monkeypatch):
    seen = []

    def fake_run(cmd, check):
        seen.append(cmd)
        seen.append(Path(cmd[cmd.index("--file") + 1]).read_text(encoding="utf-8"))
        Path(cmd[cmd.index("--write-subtitles") + 1]).write_text(
            "1\n00:00:00,000 --> 00:00:01,000\nKurs został\n\n"
            "2\n00:00:01,000 --> 00:00:02,000\nskorygowany.\n", encoding="utf-8")

    monkeypatch.setattr(narration.subprocess, "run", fake_run)
    mp3, cues = narration.run_tts("Kurs został skorygowany.", "pl-PL-ZofiaNeural", "-10%", str(tmp_path))
    assert seen == [["edge-tts", "--voice", "pl-PL-ZofiaNeural", "--rate=-10%",
                     "--file", str(tmp_path / "script.txt"),
                     "--write-media", str(tmp_path / "narration.mp3"),
                     "--write-subtitles", str(tmp_path / "narration.srt")],
                    "Kurs został skorygowany."]
    assert mp3 == str(tmp_path / "narration.mp3")
    assert cues == [[0.0, 2.0, "Kurs został skorygowany."]]


def test_audition_plays_each_voice_in_order_and_skips_failures(tmp_path):
    played = []

    def synth(voice, rate, text, mp3, pitch=None):
        assert (rate, text) == ("-10%", "Witamy z powrotem, załogo.")
        if voice == "xx-XX-BrokenNeural":
            return False
        Path(mp3).write_bytes(b"mp3")
        return True

    results = narration.audition(["pl-PL-ZofiaNeural", "xx-XX-BrokenNeural", "pl-PL-MarekNeural"],
                                 "Witamy z powrotem, załogo.", "-10%", str(tmp_path),
                                 synth=synth, player=played.append)
    assert results == [("pl-PL-ZofiaNeural", str(tmp_path / "01_pl-PL-ZofiaNeural.mp3")),
                       ("pl-PL-MarekNeural", str(tmp_path / "03_pl-PL-MarekNeural.mp3"))]
    assert played == [mp3 for _, mp3 in results]


def test_audition_passes_pitch_to_synth(tmp_path):
    pitches = []

    def synth(voice, rate, text, mp3, pitch=None):
        pitches.append(pitch)
        return True

    narration.audition(["pl-PL-ZofiaNeural", "pl-PL-MarekNeural"], "Raport.", "-15%", str(tmp_path),
                       synth=synth, pitch="-8Hz")
    assert pitches == ["-8Hz", "-8Hz"]


def test_find_player_is_none_without_afplay(monkeypatch):
    monkeypatch.setattr(narration.shutil, "which", lambda name: None)
    assert narration.find_player() is None


def test_default_voices_start_with_native_polish():
    assert narration.DEFAULT_VOICES[:2] == ["pl-PL-ZofiaNeural", "pl-PL-MarekNeural"]
