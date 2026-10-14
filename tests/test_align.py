import subprocess
import sys
from types import ModuleType, SimpleNamespace

import pytest

from muthur import align
from muthur.align import match_cues

TEXT = "Raport systemowy. Stan załogi: hibernacja. Witamy z powrotem, załogo."
S1, S2, S3 = "Raport systemowy.", "Stan załogi: hibernacja.", "Witamy z powrotem, załogo."
# Whisper word tokens carry a leading space and punctuation
HEARD = [(" Raport", 0.0, 0.4), (" systemowy.", 0.4, 1.0),
         (" Stan", 1.5, 1.8), (" załogi:", 1.8, 2.2), (" hibernacja.", 2.2, 3.0),
         (" Witamy", 3.5, 3.9), (" z", 3.9, 4.0), (" powrotem,", 4.0, 4.5), (" załogo.", 4.5, 5.0)]


def assert_cues(actual, expected):
    assert [c[2] for c in actual] == [c[2] for c in expected]
    assert [c[:2] for c in actual] == [pytest.approx(c[:2]) for c in expected]


def test_perfect_transcript():
    assert_cues(match_cues(TEXT, HEARD), [[0.0, 1.0, S1], [1.5, 3.0, S2], [3.5, 5.0, S3]])


def test_misrecognised_words_only_narrow_the_sentence():
    heard = list(HEARD)
    heard[0] = (" Rapport", 0.0, 0.4)
    heard[3] = (" załogę", 1.8, 2.2)
    heard[5] = (" Witam", 3.5, 3.9)
    assert_cues(match_cues(TEXT, heard), [[0.4, 1.0, S1], [1.5, 3.0, S2], [3.9, 5.0, S3]])


def test_missing_middle_sentence_fills_the_gap():
    assert_cues(match_cues(TEXT, HEARD[:2] + HEARD[5:]), [[0.0, 1.0, S1], [1.0, 3.5, S2], [3.5, 5.0, S3]])


def test_missing_first_sentence_starts_at_zero():
    assert_cues(match_cues(TEXT, HEARD[2:]), [[0.0, 1.5, S1], [1.5, 3.0, S2], [3.5, 5.0, S3]])


def test_missing_last_sentence_gets_minimum_slot_after_previous():
    assert_cues(match_cues(TEXT, HEARD[:5]), [[0.0, 1.0, S1], [1.5, 3.0, S2], [3.0, 3.3, S3]])


def test_consecutive_missing_sentences_split_gap_by_length():
    text = "Jeden. Dwa trzy. Cztery pięć sześć siedem. Osiem."
    cues = match_cues(text, [(" Jeden.", 0.0, 0.5), (" Osiem.", 8.0, 8.5)])
    split = 0.5 + 7.5 * 9 / 34
    assert_cues(cues, [[0.0, 0.5, "Jeden."], [0.5, split, "Dwa trzy."],
                       [split, 8.0, "Cztery pięć sześć siedem."], [8.0, 8.5, "Osiem."]])


def test_hallucinated_trailing_words_are_ignored():
    heard = HEARD + [(" Napisy", 5.5, 5.8), (" stworzone", 5.8, 6.2), (" przez", 6.2, 6.4), (" społeczność", 6.4, 7.0)]
    assert_cues(match_cues(TEXT, heard), [[0.0, 1.0, S1], [1.5, 3.0, S2], [3.5, 5.0, S3]])


def test_word_heard_out_of_order_never_moves_time_backwards():
    heard = HEARD[:2] + [(" Witamy", 1.2, 1.4)] + HEARD[2:5]
    cues = match_cues(TEXT, heard)
    assert_cues(cues, [[0.0, 1.0, S1], [1.5, 3.0, S2], [3.0, 3.3, S3]])
    assert all(a[0] <= b[0] for a, b in zip(cues, cues[1:]))


@pytest.mark.parametrize("heard", [[], [(" ...", 0.0, 0.5)]])
def test_no_usable_words_means_fallback(heard):
    assert match_cues(TEXT, heard) is None


def test_transcribe_without_faster_whisper_returns_none(monkeypatch):
    monkeypatch.setitem(sys.modules, "faster_whisper", None)
    assert align.transcribe(TEXT, "voice.mp3", "small") is None


def test_transcribe_asks_for_polish_word_timestamps_with_script_prompt(monkeypatch):
    seen = {}

    class WhisperModel:
        def __init__(self, size, **kwargs):
            seen["size"] = size

        def transcribe(self, audio, **kwargs):
            seen.update(kwargs)
            words = [SimpleNamespace(word=w, start=s, end=e) for w, s, e in HEARD]
            return [SimpleNamespace(words=words), SimpleNamespace(words=None)], None

    fake = ModuleType("faster_whisper")
    fake.WhisperModel = WhisperModel
    monkeypatch.setitem(sys.modules, "faster_whisper", fake)
    assert align.transcribe(TEXT, "voice.mp3", "base") == HEARD
    assert seen == {"size": "base", "language": "pl", "word_timestamps": True, "initial_prompt": TEXT[:800]}


def test_align_cues_returns_none_when_whisper_unavailable(monkeypatch):
    monkeypatch.setattr(align, "transcribe", lambda *a: None)
    assert align.align_cues(TEXT, "voice.mp3") is None


def test_faster_whisper_can_decode_audio(tmp_path):
    audio = pytest.importorskip("faster_whisper.audio")
    wav = tmp_path / "tone.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                    str(wav)], check=True)
    assert len(audio.decode_audio(str(wav))) == 16000
