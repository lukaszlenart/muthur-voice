import unicodedata

from muthur.text import norm_word, read_text, split_sentences

NFD = unicodedata.normalize("NFD", "Żółć gęślą jaźń.")


def test_splits_on_terminal_punctuation_keeping_it():
    assert split_sentences("Ala ma kota... A kot? Nie! Koniec") == ["Ala ma kota...", "A kot?", "Nie!", "Koniec"]


def test_colon_does_not_end_a_sentence():
    assert split_sentences("Jednostka: USCSS Montero. Stan załogi: hibernacja.") == [
        "Jednostka: USCSS Montero.", "Stan załogi: hibernacja."]


def test_line_break_without_punctuation_stays_inside_sentence():
    assert split_sentences("Raport\nsystemowy. Druga linia") == ["Raport\nsystemowy.", "Druga linia"]


def test_empty_text_has_no_sentences():
    assert split_sentences("  \n") == []


def test_norm_word_lowercases_polish_and_drops_punctuation():
    assert norm_word("ŻÓŁĆ,") == "żółć"
    assert norm_word("MU/TH/UR") == "muthur"
    assert norm_word("6000.") == "6000"
    assert norm_word(" ...") == ""


def test_read_text_drops_bom_and_composes_diacritics(tmp_path):
    path = tmp_path / "intro.txt"
    path.write_bytes(b"\xef\xbb\xbf" + NFD.encode("utf-8"))
    assert read_text(str(path)) == "Żółć gęślą jaźń."


def test_norm_word_matches_decomposed_input():
    assert norm_word(unicodedata.normalize("NFD", "Żółć,")) == "żółć"
