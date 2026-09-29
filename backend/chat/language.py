# Arabic, Arabic Supplement, Arabic Extended-A, and both Presentation Forms blocks.
_ARABIC_RANGES = (
    (0x0600, 0x06FF),
    (0x0750, 0x077F),
    (0x08A0, 0x08FF),
    (0xFB50, 0xFDFF),
    (0xFE70, 0xFEFF),
)


def _has_arabic(word: str) -> bool:
    return any(lo <= ord(ch) <= hi for ch in word for lo, hi in _ARABIC_RANGES)


def is_arabic(text: str) -> bool:
    """True when most of the words in `text` contain Arabic script.

    Deterministic on purpose: the out-of-scope path refuses before any
    generation, so there is no model call that could report the language.
    Counting words rather than letters keeps a short Arabic question that
    carries one long Latin name ("ما هي Majara؟") Arabic, while an English
    question that merely quotes an Arabic name ("What does صيت mean?") stays
    English.
    """
    # Whitespace tokens, not a \w regex: that splits a vowelled word such as
    # مُحَمَّد at each diacritic (a combining mark, not a word character).
    words = [w for w in (text or "").split() if any(ch.isalpha() for ch in w)]
    if not words:
        return False
    return sum(1 for w in words if _has_arabic(w)) * 2 > len(words)
