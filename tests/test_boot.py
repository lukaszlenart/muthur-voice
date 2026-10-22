import pytest

from muthur.boot import Step, Timing, plan, split_boot

EXAMPLE = """[BOOT start]
WZNAWIANIE SYSTEMÓW POKŁADOWYCH
[ProgressBar: 1..100, label: %, text: ROZRUCH REAKTORA]
[Status: AKTYWNE, text: System podtrzymywania życia]

[ProgressValue: -10..21, label: °C, text: TEMPERATURA POKŁADU]
[BOOT end]
Raport systemowy."""


def test_splits_steps_from_the_narrated_text():
    steps, narrated = split_boot(EXAMPLE)
    assert narrated == "Raport systemowy."
    assert steps == [
        Step("line", "WZNAWIANIE SYSTEMÓW POKŁADOWYCH", 2),
        Step("bar", "ROZRUCH REAKTORA", 3, start=1, end=100, label="%"),
        Step("status", "System podtrzymywania życia", 4, value="AKTYWNE"),
        Step("blank", "", 5),
        Step("count", "TEMPERATURA POKŁADU", 6, start=-10, end=21, label="°C"),
    ]


def test_file_without_a_block_is_returned_unchanged():
    assert split_boot("Raport systemowy.\nKoniec.") == ([], "Raport systemowy.\nKoniec.")


@pytest.mark.parametrize("start, end", [("[crt start]", "[CRT END]"), ("[Boot Start]", "[boot end]")])
def test_markers_ignore_case_and_crt_is_an_alias(start, end):
    assert split_boot(f"{start}\nA\n{end}\nB.")[0] == [Step("line", "A", 2)]


def test_tag_names_and_keys_ignore_case():
    steps, _ = split_boot("[BOOT start]\n[status: OK, TEXT: zasilanie]\n[BOOT end]\nB.")
    assert steps == [Step("status", "zasilanie", 2, value="OK")]


def test_text_may_contain_commas():
    steps, _ = split_boot("[BOOT start]\n[Status: OK, text: SYSTEM, PODSYSTEM]\n[BOOT end]\nB.")
    assert steps[0].text == "SYSTEM, PODSYSTEM"


def test_leading_blank_lines_before_the_block_are_ignored():
    steps, narrated = split_boot("\n  \n[BOOT start]\nA\n[BOOT end]\nB.")
    assert steps == [Step("line", "A", 4)] and narrated == "B."


@pytest.mark.parametrize("source, message", [
    ("[BOOT start]\n[ProgresBar: 1..100, text: R]\n[BOOT end]\nB.",
     r"line 2: unknown tag ProgresBar \(did you mean ProgressBar\?\)"),
    ("[BOOT start]\n[Status: OK]\n[BOOT end]\nB.", r"line 2: .*text"),
    ("[BOOT start]\n[ProgressValue: 1-5, text: T]\n[BOOT end]\nB.", r"line 2: .*range"),
    ("[BOOT start]\nA\nB.", r"line 1: .*\[BOOT end\]"),
    ("Wstęp.\n[BOOT start]\nA\n[BOOT end]\nB.", r"line 2: .*top"),
    ("[BOOT start]\nA\n[BOOT end]\nB.\n[Status: OK, text: T]", r"line 5: "),
    ("[BOOT start]\nA\n[BOOT end]\n", r"nothing to narrate"),
])
def test_malformed_blocks_name_the_line(source, message):
    with pytest.raises(SystemExit, match=message):
        split_boot(source)


T = Timing(type_speed=10, status_pause=1, bar_time=1, count_time=1, hold=2, gap=0)


def test_line_is_typed_at_the_type_speed():
    boot = plan([Step("line", "abcd", 1)], T, 54, False)
    assert boot.lines_at(0.15) == ["ab"]  # letter i appears at i / type_speed
    assert boot.lines_at(0.45) == ["abcd"]
    assert boot.duration == pytest.approx(0.4 + 2)


def test_clicks_fall_on_typed_letters_but_not_spaces():
    assert plan([Step("line", "a b", 1)], T, 54, False).clicks == pytest.approx([0.0, 0.2])


def test_status_values_line_up_after_the_pause():
    steps = [Step("status", "ATMOSFERA", 1, value="OK"), Step("status", "OŚWIETLENIE", 2, value="WŁĄCZONE")]
    boot = plan(steps, T, 54, False)
    assert boot.lines_at(boot.duration) == ["ATMOSFERA ..... OK", "OŚWIETLENIE ... WŁĄCZONE"]
    typed = len("ATMOSFERA ..... ") / 10
    assert boot.lines_at(typed + 0.5) == ["ATMOSFERA ..... "]


def test_bar_fills_and_counts_to_the_end_value():
    boot = plan([Step("bar", "R", 1, start=1, end=100, label="%")], T, 54, False)
    assert boot.lines_at(0.2 + 0.4) == ["R " + "█" * 6 + "░" * 9 + "  " + "41%"]
    assert boot.lines_at(boot.duration) == ["R " + "█" * 15 + "  100%"]


def test_value_counts_through_whole_numbers():
    boot = plan([Step("count", "T", 1, start=-10, end=21, label="°C")], T, 54, False)
    assert boot.lines_at(boot.duration)[0].endswith("21°C")
    assert boot.lines_at(len("T ... ") / 10)[0].endswith("-10°C")


def test_upper_casing_skips_the_label():
    boot = plan([Step("count", "ciśnienie", 1, start=1, end=2, label="kPa")], T, 54, True)
    assert boot.lines_at(boot.duration) == ["CIŚNIENIE ... 2kPa"]


def test_line_wider_than_wrap_names_the_line():
    with pytest.raises(SystemExit, match=r"line 7: .*--wrap is 10"):
        plan([Step("status", "TEMPERATURA", 7, value="OK")], T, 10, False)


def test_start_delays_the_whole_screen():
    boot = plan([Step("line", "ab", 1)], Timing(type_speed=10, hold=2, gap=0, start=0.6), 54, False)
    assert boot.lines_at(0.5) == []
    assert boot.clicks == pytest.approx([0.6, 0.7])
    assert boot.duration == pytest.approx(0.6 + 0.2 + 2)
