import pytest

from muthur.boot import Step, split_boot

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
