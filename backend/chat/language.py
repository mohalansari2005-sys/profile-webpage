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


# How visitors write this site's names in Arabic script. The companies are
# transliterations, so an English-only corpus embeds nowhere near them and a
# model can read them as similar-looking Arabic words. Mapping the known
# spellings back to the Latin names is deterministic and needs no model call.
#
# Spellings that are only ever this name. "ماجرة" is an older spelling of
# Majara; the current one is "مجرة" (below).
NAME_ALIASES = {
    "Majara": ("ماجرة", "ماجره", "ماجراة", "ماجارا"),
    "SEET": ("صيت",),
    "Keyraa": ("كيرا", "كايرا", "كيرآ"),
}

# Spellings that are also ordinary words: "مجرة" (also typed "مجره") is Majara,
# and also the Arabic word for "galaxy". These are read as the company only
# when they stand alone as a proper noun: no definite article ("المجرة", "the
# galaxy") and no "lil-" ("للمجرة", "to the galaxy"), and at most a one-letter
# and/in/for prefix ("في مجرة", "بمجرة", "ولمجرة").
AMBIGUOUS_ALIASES = {
    "Majara": ("مجرة", "مجره"),
}

# Told to the models that read the question, so a spelling not in the tables
# above is still recognised.
NAME_GLOSSARY = (
    "Names written in Arabic script: مجرة (also written مجره, and formerly "
    "ماجرة) is Majara, Mohammed's employer, a company, and not the Arabic word "
    "for galaxy; صيت is SEET (a company he worked at); كيرا is Keyraa (a hotel "
    "booking project). They are names, not ordinary Arabic words."
)

_ARABIC_LETTER = "\u0621-\u064a"


def _alias_pattern(spellings: tuple[str, ...], prefix: str) -> re.Pattern:
    words = "|".join(map(re.escape, spellings))
    return re.compile(
        rf"(?<![{_ARABIC_LETTER}])({prefix})(?:{words})(?![{_ARABIC_LETTER}])"
    )


# Optional prefix, kept in the output so the sentence still reads: and/so
# (و ف), then in-with/like/for (ب ك ل) optionally fused with "al-" (ال), or
# "lil-" (لل). Stacks such as والماجرة, بالماجرة, للماجرة and وللماجرة.
_ANY_PREFIX = "[وف]?(?:[بكل]?ال|لل|[بكل])?"
_ONE_LETTER_PREFIX = "[وف]?[بكل]?"

_ALIAS = [
    *((_alias_pattern(sp, _ANY_PREFIX), name) for name, sp in NAME_ALIASES.items()),
    *((_alias_pattern(sp, _ONE_LETTER_PREFIX), name) for name, sp in AMBIGUOUS_ALIASES.items()),
]


def normalize_names(text: str) -> str:
    """Rewrites known Arabic spellings of the site's names to their Latin form."""
    for pattern, name in _ALIAS:
        text = pattern.sub(lambda m: f"{m.group(1)} {name}".strip(), text or "")
    return text
