import os

import pytest

from muthur import cli


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def toml(workdir):
    def write(content, name="muthur.toml"):
        path = workdir / name
        path.write_text(content, encoding="utf-8")
        return path
    return write


def test_no_file_keeps_built_in_defaults(workdir, capsys):
    a = cli.parse_args(["render", "intro.txt"])
    assert (a.voice, a.rate, a.wrap, a.hum, a.upper, a.tts, a.align) == (
        "pl-PL-ZofiaNeural", "-20%", 54, True, True, True, True)
    assert "config:" not in capsys.readouterr().out


def test_file_beats_built_in_default(toml):
    toml('[render]\nrate = "-10%"\nwrap = 40\n')
    a = cli.parse_args(["render", "intro.txt"])
    assert (a.rate, a.wrap) == ("-10%", 40)


def test_flag_beats_file(toml):
    toml('[render]\nrate = "-10%"\n')
    assert cli.parse_args(["render", "intro.txt", "--rate=-15%"]).rate == "-15%"


def test_prints_the_config_file_used(toml, capsys):
    path = toml('[render]\nrate = "-10%"\n')
    cli.parse_args(["render", "intro.txt"])
    assert capsys.readouterr().out == f"  config: {path}\n"


@pytest.mark.parametrize("position", ["before", "after"])
def test_config_flag_picks_another_file(toml, position):
    toml('[render]\nrate = "-10%"\n')
    other = toml('[render]\nrate = "-30%"\n', name="sesja2.toml")
    args = ["render", "intro.txt"]
    args = ["render", "--config", str(other), "intro.txt"] if position == "before" else [*args, "--config", str(other)]
    assert cli.parse_args(args).rate == "-30%"


def test_missing_config_file_is_an_error(workdir):
    with pytest.raises(SystemExit, match="brak.toml"):
        cli.parse_args(["render", "intro.txt", "--config", "brak.toml"])


def test_invalid_toml_names_the_file(toml):
    toml('[render\nrate = "-10%"\n')
    with pytest.raises(SystemExit, match="muthur.toml"):
        cli.parse_args(["render", "intro.txt"])


@pytest.mark.parametrize("content, key", [
    ('[render]\nimge = "a.jpg"\n', "[render].imge"),
    ('[render]\ntext = "intro.txt"\n', "[render].text"),
    ('[render]\nno_hum = true\n', "[render].no_hum"),
    ('[render]\nconfig = "x.toml"\n', "[render].config"),
    ('[rendr]\nrate = "-10%"\n', "[rendr]"),
])
def test_unknown_key_or_section_is_rejected(toml, content, key):
    toml(content)
    with pytest.raises(SystemExit, match=f"unknown .*{key.replace('[', r'\[').replace(']', r'\]')}"):
        cli.parse_args(["render", "intro.txt"])


@pytest.mark.parametrize("content, key", [
    ('[render]\nwrap = "54"\n', "wrap"),
    ('[render]\nwrap = true\n', "wrap"),
    ('[render]\nhum = "no"\n', "hum"),
    ('[render]\nrate = -10\n', "rate"),
    ('[render]\nvoice = ["pl-PL-ZofiaNeural"]\n', "voice"),
    ('[render]\nvoice_fx = "reverb"\n', "voice_fx"),
    ('[voices]\nvoice = "pl-PL-ZofiaNeural"\n', "voice"),
    ('[voices]\nvoice = [1, 2]\n', "voice"),
])
def test_wrong_value_type_is_rejected(toml, content, key):
    toml(content)
    with pytest.raises(SystemExit, match=f"\\].{key}"):
        cli.parse_args(["render", "intro.txt"])


def test_relative_paths_resolve_against_the_config_folder(workdir, monkeypatch):
    (workdir / "kampania").mkdir()
    (workdir / "kampania" / "muthur.toml").write_text(
        '[render]\nimage = "montero.jpg"\naudio = "dzwiek/lektor.mp3"\nsrt = "a.srt"\n'
        'font = "f.ttf"\nout = "film.mp4"\n\n[voices]\nkeep = "probki"\n', encoding="utf-8")
    cfg = str(workdir / "kampania" / "muthur.toml")
    base = workdir / "kampania"
    a = cli.parse_args(["render", "intro.txt", "--config", cfg])
    assert (a.image, a.audio, a.srt, a.font, a.out) == (
        str(base / "montero.jpg"), str(base / "dzwiek" / "lektor.mp3"), str(base / "a.srt"),
        str(base / "f.ttf"), str(base / "film.mp4"))
    assert cli.parse_args(["voices", "--config", cfg]).keep == str(base / "probki")


def test_absolute_paths_stay_as_they_are(toml):
    image = os.path.abspath(os.path.join(os.sep, "obrazy", "montero.jpg"))
    toml(f"[render]\nimage = '{image}'\n")
    assert cli.parse_args(["render", "intro.txt"]).image == image


def test_cli_paths_stay_relative_to_the_current_directory(toml):
    toml('[render]\nimage = "montero.jpg"\n')
    assert cli.parse_args(["render", "intro.txt", "--image", "inny.jpg"]).image == "inny.jpg"


@pytest.mark.parametrize("key", ["hum", "upper", "tts", "align"])
def test_false_in_the_file_switches_the_option_off(toml, key):
    toml(f'[render]\naudio = "v.mp3"\n{key} = false\n')
    assert getattr(cli.parse_args(["render", "intro.txt"]), key) is False


@pytest.mark.parametrize("key", ["hum", "upper", "tts", "align"])
def test_positive_flag_overrides_false_in_the_file(toml, key):
    toml(f'[render]\n{key} = false\n')
    assert getattr(cli.parse_args(["render", "intro.txt", f"--{key}"]), key) is True


@pytest.mark.parametrize("key", ["hum", "upper", "tts", "align"])
def test_no_flags_still_work(workdir, key):
    assert getattr(cli.parse_args(["render", "intro.txt", "--audio", "v.mp3", f"--no-{key}"]), key) is False


def test_voices_play_maps_from_the_file(toml):
    toml('[voices]\nplay = false\n')
    assert cli.parse_args(["voices"]).play is False


def test_voices_picks_up_the_list_from_the_file(toml, monkeypatch):
    toml('[voices]\nvoice = ["pl-PL-MarekNeural", "pl-PL-ZofiaNeural"]\nrate = "-15%"\n')
    heard = []
    monkeypatch.setattr(cli.narration, "find_player", lambda: print)
    monkeypatch.setattr(cli.narration, "audition",
                        lambda voices, text, rate, *a, **k: heard.append((voices, rate)) or [("v", "v.mp3")])
    cli.main(["voices"])
    assert heard == [(["pl-PL-MarekNeural", "pl-PL-ZofiaNeural"], "-15%")]


def test_voice_flag_replaces_the_list_from_the_file(toml, monkeypatch):
    toml('[voices]\nvoice = ["pl-PL-MarekNeural", "pl-PL-ZofiaNeural"]\n')
    heard = []
    monkeypatch.setattr(cli.narration, "find_player", lambda: print)
    monkeypatch.setattr(cli.narration, "audition",
                        lambda voices, *a, **k: heard.append(voices) or [("v", "v.mp3")])
    cli.main(["voices", "--voice", "de-DE-SeraphinaMultilingualNeural"])
    assert heard == [["de-DE-SeraphinaMultilingualNeural"]]


def test_polish_text_round_trips_unchanged(toml):
    toml('[render]\ntitle = "MU/TH/UR 6000 :: ŁÓDŹ ŻÓŁTA"\n\n'
         '[voices]\ntext = "Procedura wybudzania zakończona. Witamy z powrotem, załogo."\n')
    assert cli.parse_args(["render", "intro.txt"]).title == "MU/TH/UR 6000 :: ŁÓDŹ ŻÓŁTA"
    assert cli.parse_args(["voices"]).text == "Procedura wybudzania zakończona. Witamy z powrotem, załogo."


@pytest.mark.parametrize("content, message", [
    ('[render]\nsrt = "a.srt"\n', "srt in muthur.toml needs audio"),
    ('[render]\nalign = false\n', "align in muthur.toml needs audio"),
])
def test_setting_from_the_file_that_needs_audio_names_the_file(toml, capsys, content, message):
    toml(content)
    with pytest.raises(SystemExit):
        cli.main(["render", "intro.txt"])
    assert message in capsys.readouterr().err


def test_flag_that_needs_audio_still_names_the_flag(toml, capsys):
    toml('[render]\nsrt = "a.srt"\n')
    with pytest.raises(SystemExit):
        cli.main(["render", "intro.txt", "--srt", "b.srt"])
    assert "--srt needs --audio" in capsys.readouterr().err


@pytest.fixture
def float_flag(monkeypatch):
    original = cli.build_parser

    def with_pace():
        parser = original()
        cli.subcommands(parser)["render"].add_argument("--pace", type=float, default=1.0)
        return parser
    monkeypatch.setattr(cli, "build_parser", with_pace)


@pytest.mark.parametrize("content, expected", [("pace = 2.5", 2.5), ("pace = 2", 2.0)])
def test_number_setting_accepts_decimals_and_whole_numbers(toml, float_flag, content, expected):
    toml(f"[render]\n{content}\n")
    assert cli.parse_args(["render", "intro.txt"]).pace == expected


@pytest.mark.parametrize("content", ['pace = "2.5"', "pace = true"])
def test_number_setting_rejects_strings_and_booleans(toml, float_flag, content):
    toml(f"[render]\n{content}\n")
    with pytest.raises(SystemExit, match=r"\]\.pace must be a number"):
        cli.parse_args(["render", "intro.txt"])
