import unicodedata

import pytest

from muthur.timing import estimate_cues, merge_into_sentences, parse_srt, srt_time, write_srt


def test_srt_time_accepts_comma_and_dot():
    assert srt_time("00:01:02,345") == pytest.approx(62.345)
    assert srt_time("01:00:00.250") == pytest.approx(3600.25)


def test_merges_cues_split_mid_sentence():
    cues = [[0, 1, "Kurs został"], [1, 2, "skorygowany."], [2, 3, "Ale"], [3, 4, "coś: tak"]]
    assert merge_into_sentences(cues) == [[0, 2, "Kurs został skorygowany."], [2, 4, "Ale coś: tak"]]


def test_colon_closes_a_cue():
    assert merge_into_sentences([[0, 1, "Stan załogi:"], [1, 2, "hibernacja."]]) == [
        [0, 1, "Stan załogi:"], [1, 2, "hibernacja."]]


def test_parse_srt_handles_crlf_multiline_and_merging(tmp_path):
    srt = tmp_path / "n.srt"
    srt.write_bytes((
        "1\r\n00:00:00,000 --> 00:00:01,000\r\nKurs\r\nzostał\r\n\r\n"
        "2\r\n00:00:01,000 --> 00:00:02,500\r\nskorygowany.\r\n\r\n"
        "garbage block without timestamp\r\n\r\n"
        "3\r\n00:00:03,000 --> 00:00:04,000\r\nWitamy z powrotem, załogo.\r\n"
    ).encode("utf-8"))
    assert parse_srt(str(srt)) == [
        [0.0, 2.5, "Kurs został skorygowany."],
        [3.0, 4.0, "Witamy z powrotem, załogo."],
    ]


def test_write_srt_format_and_round_trip(tmp_path):
    path = tmp_path / "out.srt"
    cues = [[0.0, 1.5, "Raport systemowy."], [3723.4567, 3725.0, "Stan załogi: hibernacja."]]
    write_srt(cues, str(path))
    assert path.read_text(encoding="utf-8") == (
        "1\n00:00:00,000 --> 00:00:01,500\nRaport systemowy.\n\n"
        "2\n01:02:03,457 --> 01:02:05,000\nStan załogi: hibernacja.\n\n")
    assert parse_srt(str(path)) == [[0.0, 1.5, "Raport systemowy."],
                                    [pytest.approx(3723.457), 3725.0, "Stan załogi: hibernacja."]]


def test_estimate_cues_uses_length_with_minimum_and_gap():
    cues = estimate_cues("Krótko. " + "a" * 26 + ".")
    assert cues[0] == [0.0, 1.5, "Krótko."]
    assert cues[1][0] == pytest.approx(1.85)
    assert cues[1][1] == pytest.approx(1.85 + 27 / 13)


def test_srt_time_pads_shortened_fraction():
    assert srt_time("00:00:12,5") == pytest.approx(12.5)
    assert srt_time("00:00:12.25") == pytest.approx(12.25)


def test_parse_srt_with_bom_and_decomposed_text(tmp_path):
    srt = tmp_path / "napisy.srt"
    srt.write_bytes(b"\xef\xbb\xbf" + unicodedata.normalize(
        "NFD", "1\n00:00:00,000 --> 00:00:01,000\nŻółć gęślą jaźń.\n").encode("utf-8"))
    assert parse_srt(str(srt)) == [[0.0, 1.0, "Żółć gęślą jaźń."]]
