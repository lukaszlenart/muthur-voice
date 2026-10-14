from muthur.text import norm_word, split_sentences


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
