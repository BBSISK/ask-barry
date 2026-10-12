"""Check that a model's quote really appears in the sources (Stage 6), shared by the evaluators and the
capability builder (ASK-42): a judge that may quote must not be able to invent its evidence."""
import re


def _norm(text):
    """Lowercase word tokens only: ignores markdown, HTML tags, ANSI codes, punctuation, emoji and spacing."""
    text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", " ", str(text or ""))       # ANSI colour codes the model sometimes emits
    text = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", " ", text)                 # other control characters
    text = re.sub(r"\[([^\]]*)\]\([^)\s]*\)", r"\1", text)            # [link text](url) -> link text (ASK-60)
    text = re.sub(r"https?://\S+", " ", text)                           # bare URLs: the judge rarely copies them
    text = re.sub(r"<[^>]{0,40}>", " ", text.lower())
    return " " + " ".join(re.findall(r"\w+", text)) + " "


def _fuzzy_in(q, hay, min_share=0.8):
    """True if at least min_share of the quote's words appear, in order, within a short window of the sources.

    Tolerates small rewordings by the judge ("Render auto-deploys the Docker container" vs
    "Render auto-deploys Docker container") but not invented content words.
    """
    need = max(3, int(len(q) * min_share + 0.999))
    window = len(q) * 2 + 2
    for start, word in enumerate(hay):
        if word not in q[:len(q) - need + 1]:
            continue
        matched, qi = 0, q.index(word, 0, len(q) - need + 1)
        for w in hay[start:start + window]:
            if qi < len(q) and w == q[qi]:
                matched, qi = matched + 1, qi + 1
            else:
                while qi < len(q) and w != q[qi] and w in q[qi + 1:]:
                    qi += 1                       # the judge added a word the sources don't have
                if qi < len(q) and w == q[qi]:
                    matched, qi = matched + 1, qi + 1
        if matched >= need:
            return True
    return False


MIN_RUN = 4    # ASK-60: words in each exact run of an elided quote


def _elided_in(q, hay, min_run=MIN_RUN):
    """True if the quote is the section's own words with passages left out: every quote word is covered by exact
    runs of min_run+ words that appear in the section in the same order. The judge often drops a sentence
    without writing "..."; a run that short can't be stitched into a claim the section doesn't make."""
    i, pos = 0, 0
    while i < len(q):
        best, at = 0, -1
        for start in range(pos, len(hay)):
            k = 0
            while i + k < len(q) and start + k < len(hay) and hay[start + k] == q[i + k]:
                k += 1
            if k > best:
                best, at = k, start
        if best < min(min_run, len(q) - i) or best < 2:
            return False
        i, pos = i + best, at + best
    return True


def quote_in_sources(quote, sources_text, elided=False):
    """True if every substantial piece of the judge's quote (split on "..." and line breaks) is in the sources.

    Matching is on whole words, ignoring formatting. Exact word sequences of 3+ words or 12+
    characters pass; otherwise 80%+ of a 5+ word fragment must appear in order nearby AND every content word
    (4+ letters) must occur in the sources, so a light rewording passes but new content doesn't.

    elided=True (the capability judge, ASK-60) also accepts the section's words with passages left out (see
    _elided_in), and a short quote of 2+ words found exactly, such as a command ("mvn test").
    """
    haystack = _norm(sources_text)
    hay_words = haystack.split()
    vocab = set(hay_words)

    def found(frag):
        f = _norm(frag)
        words = f.split()
        if f in haystack:
            return True
        if elided and _elided_in(words, hay_words):
            return True
        new_content = [w for w in words if len(w) >= 4 and w not in vocab]
        return len(words) >= 5 and not new_content and _fuzzy_in(words, hay_words)

    # The judge may join separate passages with "..." or a line break: every substantial piece must be found.
    pieces = [p for p in re.split(r"\.\.\.|…|\n", str(quote or ""))
              if len(_norm(p).split()) >= 3 or len(_norm(p).strip()) >= 12]
    if not pieces and elided:
        short = _norm(quote)
        return len(short.split()) >= 2 and short in haystack
    return bool(pieces) and all(found(p) for p in pieces)
