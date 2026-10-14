import pytest

from golden.harness import FakeFFmpeg
from muthur.mux import encode, ffmpeg_command

VIDEO_IN = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", "1920x1080", "-r", "25", "-i", "-"]


def video_out(total, out):
    return ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
            "-t", total, "-movflags", "+faststart", out]


AAC = ["-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
HUM = "anoisesrc=color=brown:amplitude=0.6:seed=7"


def test_voice_and_hum_are_mixed():
    assert ffmpeg_command(10.43, "voice.mp3", True, "o.mp4") == VIDEO_IN + [
        "-i", "voice.mp3", "-f", "lavfi", "-t", "10.43", "-i", HUM,
        "-filter_complex",
        "[1:a]adelay=2000|2000,aecho=0.8:0.5:40:0.12[v];"
        "[2:a]lowpass=f=180,volume=0.25,afade=t=in:d=2,afade=t=out:st=8.43:d=2[h];"
        "[v][h]amix=inputs=2:duration=longest:normalize=0[a]",
        "-map", "0:v", *AAC] + video_out("10.43", "o.mp4")


def test_hum_only():
    assert ffmpeg_command(10.43, None, True, "o.mp4") == VIDEO_IN + [
        "-f", "lavfi", "-t", "10.43", "-i", HUM,
        "-filter_complex", "[1:a]lowpass=f=180,volume=0.25,afade=t=in:d=2,afade=t=out:st=8.43:d=2[h];[h]anull[a]",
        "-map", "0:v", *AAC] + video_out("10.43", "o.mp4")


def test_voice_only():
    assert ffmpeg_command(6.0, "voice.mp3", False, "o.mp4") == VIDEO_IN + [
        "-i", "voice.mp3",
        "-filter_complex", "[1:a]adelay=2000|2000,aecho=0.8:0.5:40:0.12[v];[v]anull[a]",
        "-map", "0:v", *AAC] + video_out("6.00", "o.mp4")


def test_silent_video_has_no_audio_stream():
    assert ffmpeg_command(6.0, None, False, "o.mp4") == VIDEO_IN + ["-map", "0:v"] + video_out("6.00", "o.mp4")


def test_encode_pipes_every_frame(monkeypatch):
    procs = []
    monkeypatch.setattr("subprocess.Popen", lambda cmd, stdin=None: procs.append(FakeFFmpeg(cmd)) or procs[-1])
    encode([(0.0, b"a"), (0.04, b"b")], 0.08, ["ffmpeg"], "o.mp4")
    assert len(procs[0].frames) == 2


def test_encode_exits_when_ffmpeg_fails(monkeypatch):
    def failing(cmd, stdin=None):
        proc = FakeFFmpeg(cmd)
        proc.returncode = 1
        return proc
    monkeypatch.setattr("subprocess.Popen", failing)
    with pytest.raises(SystemExit, match="ffmpeg failed"):
        encode([(0.0, b"a")], 0.04, ["ffmpeg"], "o.mp4")
