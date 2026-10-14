from pathlib import Path

from muthur import narration


def test_edge_tts_cmd_for_a_file_matches_prototype():
    assert narration.edge_tts_cmd("pl-PL-ZofiaNeural", "-10%", "n.mp3", file="intro.txt", srt="n.srt") == [
        "edge-tts", "--voice", "pl-PL-ZofiaNeural", "--rate=-10%", "--file", "intro.txt",
        "--write-media", "n.mp3", "--write-subtitles", "n.srt"]


def test_edge_tts_cmd_for_inline_text_survives_leading_dash():
    assert narration.edge_tts_cmd("pl-PL-MarekNeural", "+0%", "s.mp3", text="-- Raport.") == [
        "edge-tts", "--voice", "pl-PL-MarekNeural", "--rate=+0%", "--text=-- Raport.", "--write-media", "s.mp3"]


def test_run_tts_returns_sentence_cues(tmp_path, monkeypatch):
    seen = []

    def fake_run(cmd, check):
        seen.append(cmd)
        Path(cmd[cmd.index("--write-subtitles") + 1]).write_text(
            "1\n00:00:00,000 --> 00:00:01,000\nKurs został\n\n"
            "2\n00:00:01,000 --> 00:00:02,000\nskorygowany.\n", encoding="utf-8")

    monkeypatch.setattr(narration.subprocess, "run", fake_run)
    mp3, cues = narration.run_tts("intro.txt", "pl-PL-ZofiaNeural", "-10%", str(tmp_path))
    assert mp3 == str(tmp_path / "narration.mp3")
    assert seen == [["edge-tts", "--voice", "pl-PL-ZofiaNeural", "--rate=-10%", "--file", "intro.txt",
                     "--write-media", str(tmp_path / "narration.mp3"),
                     "--write-subtitles", str(tmp_path / "narration.srt")]]
    assert cues == [[0.0, 2.0, "Kurs został skorygowany."]]
