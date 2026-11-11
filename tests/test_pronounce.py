import os

import pytest

from muthur import cli
from muthur.text import respell, restore

WORDS = {"Weyland-Yutani": "Łejland-Jutani", "Anchorpoint": "Ankorpojnt"}


def spoken(text, pronounce=WORDS):
    return respell(text, pronounce)[0]


def test_respell_replaces_every_occurrence():
    assert spoken("Z Anchorpoint do Anchorpoint.") == "Z Ankorpojnt do Ankorpojnt."


def test_respell_keeps_polish_endings():
    assert spoken("Ze stacji Anchorpointu, od Weyland-Yutani.") == "Ze stacji Ankorpojntu, od Łejland-Jutani."


def test_respell_ignores_a_match_inside_a_word():
    assert spoken("XAnchorpoint") == "XAnchorpoint"


def test_respell_prefers_the_longest_written_form():
    assert spoken("Weyland-Yutani i Weyland.", {"Weyland": "Łejland", "Weyland-Yutani": "Łejland-Jutani"}) == (
        "Łejland-Jutani i Łejland.")


def test_respell_does_not_respell_its_own_output():
    assert spoken("A B", {"A": "B", "B": "C"}) == "B C"


def test_respell_ignores_case():
    assert spoken('Cenny "hel-3", HEL-3 i Hel-3.', {"Hel-3": "hel trzy"}) == 'Cenny "hel trzy", hel trzy i hel trzy.'


def test_restore_undoes_respell_keeping_each_original_case():
    text = "Hel-3 ze stacji ANCHORPOINT, Anchorpointu i hel-3, od Weyland-Yutani."
    pronounce = dict(WORDS, **{"hel-3": "hel trzy"})
    said, replaced = respell(text, pronounce)
    assert restore(said, pronounce, iter(replaced)) == text


def test_restore_consumes_replaced_words_across_calls():
    pronounce = {"hel-3": "hel trzy"}
    replaced = iter(["HEL-3", "Hel-3"])
    assert [restore(s, pronounce, replaced) for s in ["Rozpad w hel trzy.", "Cenny hel trzy."]] == [
        "Rozpad w HEL-3.", "Cenny Hel-3."]


def test_restore_without_record_uses_the_configured_spelling():
    assert restore("Ze stacji ankorpojnt.", WORDS, iter([])) == "Ze stacji Anchorpoint."


def test_restore_tolerates_changed_spacing():
    assert restore("Ze stacji Ankor\npojnt.", {"Anchorpoint": "Ankor pojnt"}, iter([])) == "Ze stacji Anchorpoint."


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "intro.txt").write_text("Kurs na Anchorpoint. Zlecenie od Weyland-Yutani.\n", encoding="utf-8")
    return tmp_path


def write_config(workdir, body):
    (workdir / "muthur.toml").write_text(body, encoding="utf-8")


def test_pronounce_section_reaches_render(workdir):
    write_config(workdir, '[pronounce]\n"Weyland-Yutani" = "Łejland-Jutani"\n')
    assert cli.parse_args(["render", "intro.txt"]).pronounce == {"Weyland-Yutani": "Łejland-Jutani"}


def test_no_pronounce_section_means_no_respelling(workdir):
    assert cli.parse_args(["render", "intro.txt"]).pronounce == {}


@pytest.mark.parametrize("body, problem", [
    ('[pronounce]\nAnchorpoint = 3\n', "[pronounce].Anchorpoint must be a string"),
    ('[pronounce]\nAnchorpoint = "Ankor. Pojnt"\n', "[pronounce].Anchorpoint must not contain . ! ? or :"),
    ('[pronounce]\nAnchorpoint = "  "\n', "[pronounce].Anchorpoint must not be empty"),
    ('[pronounce]\n"" = "nic"\n', "[pronounce] has an empty word"),
    ('pronounce = "Anchorpoint"\n', "unknown section [pronounce]"),
])
def test_bad_pronounce_entries_are_rejected(workdir, body, problem):
    write_config(workdir, body)
    with pytest.raises(SystemExit) as exit:
        cli.parse_args(["render", "intro.txt"])
    assert problem in str(exit.value.code)


def test_tts_reads_the_spoken_form_and_the_screen_shows_the_written_one(workdir, monkeypatch):
    write_config(workdir, '[pronounce]\nAnchorpoint = "Ankorpojnt"\n"Weyland-Yutani" = "Łejland-Jutani"\n')
    spoken, screens = [], []

    def fake_tts(text, voice, rate, tmp, pitch=None):
        spoken.append(text)
        mp3 = os.path.join(tmp, "narration.mp3")
        open(mp3, "wb").close()
        return mp3, [[0.0, 1.0, "Kurs na"], [1.0, 2.0, "Ankorpojnt."], [2.0, 3.0, "Zlecenie od Łejland-Jutani."]]

    monkeypatch.setattr(cli.narration, "run_tts", fake_tts)
    monkeypatch.setattr(cli, "render_video", lambda cues, *a, **k: screens.append(cues))
    cli.main(["render", "intro.txt"])
    assert spoken == ["Kurs na Ankorpojnt. Zlecenie od Łejland-Jutani."]
    assert [c[2] for c in screens[0]] == ["Kurs na", "Anchorpoint.", "Zlecenie od Weyland-Yutani."]


def test_whisper_matches_the_spoken_form(workdir, monkeypatch):
    write_config(workdir, '[pronounce]\nAnchorpoint = "Ankorpojnt"\n')
    (workdir / "voice.mp3").write_bytes(b"")
    seen, screens = [], []

    def fake_align(text, audio, size):
        seen.append(text)
        return [[0.0, 1.0, "Kurs na Ankorpojnt."], [1.0, 2.0, "Zlecenie od Weyland-Yutani."]]

    monkeypatch.setattr(cli.align, "align_cues", fake_align)
    monkeypatch.setattr(cli, "render_video", lambda cues, *a, **k: screens.append(cues))
    cli.main(["render", "intro.txt", "--audio", "voice.mp3"])
    assert seen == ["Kurs na Ankorpojnt. Zlecenie od Weyland-Yutani."]
    assert [c[2] for c in screens[0]][0] == "Kurs na Anchorpoint."
