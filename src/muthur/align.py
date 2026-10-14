import difflib

from muthur.text import norm_word, split_sentences


def align_cues(text, audio, model_size="small"):
    words = transcribe(text, audio, model_size)
    return None if words is None else match_cues(text, words)


def transcribe(text, audio, model_size):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("  ! faster-whisper not installed (uv sync --extra align), estimating timing")
        return None

    print(f"  aligning subtitles with Whisper ({model_size}), first run downloads the model...")
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(audio, language="pl", word_timestamps=True,
                                   initial_prompt=text[:800])
    return [(w.word, w.start, w.end) for s in segments for w in (s.words or [])]


def match_cues(text, words):
    """Find when each sentence of `text` is spoken, given Whisper's timed words.

    The recognised words are matched against the script words (difflib), so
    small recognition mistakes don't matter. Sentences with no matched word get
    a time slot interpolated from their neighbours.
    """
    rec = [(norm_word(w), st, en) for w, st, en in words]
    rec = [r for r in rec if r[0]]
    if not rec:
        print("  ! Whisper recognised no words, estimating timing")
        return None

    sentences = split_sentences(text)
    script, owner = [], []
    for i, s in enumerate(sentences):
        for w in s.split():
            n = norm_word(w)
            if n:
                script.append(n)
                owner.append(i)

    times = [[] for _ in sentences]
    sm = difflib.SequenceMatcher(None, script, [r[0] for r in rec], autojunk=False)
    for a, b, size in sm.get_matching_blocks():
        for k in range(size):
            _, st, en = rec[b + k]
            times[owner[a + k]].append((st, en))

    cues = [[min(t[0] for t in ts), max(t[1] for t in ts), s] if ts else [None, None, s]
            for ts, s in zip(times, sentences)]
    matched = sum(1 for c in cues if c[0] is not None)
    print(f"  matched {matched}/{len(cues)} sentences")

    # fill sentences Whisper missed, proportionally to their length
    end_of_audio = rec[-1][2]
    i = 0
    while i < len(cues):
        if cues[i][0] is not None:
            i += 1
            continue
        j = i
        while j < len(cues) and cues[j][0] is None:
            j += 1
        lo = cues[i - 1][1] if i > 0 else 0.0
        hi = cues[j][0] if j < len(cues) else end_of_audio
        total = sum(len(c[2]) for c in cues[i:j]) or 1
        t = lo
        for c in cues[i:j]:
            d = (hi - lo) * len(c[2]) / total
            c[0], c[1] = t, t + d
            t += d
        i = j
    for k in range(1, len(cues)):  # keep order monotonic
        cues[k][0] = max(cues[k][0], cues[k - 1][0])
        cues[k][1] = max(cues[k][1], cues[k][0] + 0.3)
    return cues
