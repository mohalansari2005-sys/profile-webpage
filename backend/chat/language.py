import re

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


# How visitors write this site's names in Arabic script. "ماجرة" is a
# transliteration, not a word, so an English-only corpus embeds nowhere near it
# and a model can read it as a similar-looking Arabic word. Mapping the known
# spellings back to the Latin names is deterministic and needs no model call.
NAME_ALIASES = {
    "Majara": ("ماجرة", "ماجراة", "ماجارا", "ماجرا"),
    "SEET": ("صيت", "سيت"),
    "Keyraa": ("كيرا", "كايرا", "كيرآ"),
}

# Told to the models that read the question, so a spelling not in the table
# above is still recognised.
NAME_GLOSSARY = (
    "Names written in Arabic script: ماجرة is Majara (Mohammed's employer, a "
    "company), صيت is SEET (a company he worked at), كيرا is Keyraa (a hotel "
    "booking project). They are names, not ordinary Arabic words."
)

_ARABIC_LETTER = "\u0621-\u064a"
# Optional one-letter or definite-article prefix (in/by/for/like/and, "al-"),
# kept in the output so the sentence still reads.
_ALIAS = [
    (re.compile(
        rf"(?<![{_ARABIC_LETTER}])((?:[وبلكف]|ال)?)(?:{'|'.join(map(re.escape, spellings))})(?![{_ARABIC_LETTER}])"
    ), name)
    for name, spellings in NAME_ALIASES.items()
]


def normalize_names(text: str) -> str:
    """Rewrites known Arabic spellings of the site's names to their Latin form."""
    for pattern, name in _ALIAS:
        text = pattern.sub(lambda m: f"{m.group(1)} {name}".strip(), text or "")
    return text
