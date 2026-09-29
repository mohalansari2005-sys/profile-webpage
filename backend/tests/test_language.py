import pytest

from chat.language import is_arabic


@pytest.mark.parametrize("text", [
    "ما هي ماجرة؟",
    "ماذا فعل محمد في صيت؟",
    "ما هي Majara؟",  # Arabic sentence carrying a Latin name
    "ماذا يعني  ١٢٣ ؟",
    "من هو مُحَمَّد؟",  # vowelled (diacritized) Arabic
])
def test_arabic_questions_are_detected(text):
    assert is_arabic(text) is True


@pytest.mark.parametrize("text", [
    "What is Majara?",
    "What does صيت mean?",  # English sentence quoting an Arabic name
    "",
    "What does \u0645\u064f\u062d\u064e\u0645\u0651\u064e\u062f mean?",  # vowelled Arabic name
    "1234 ?!",
    None,
])
def test_non_arabic_text_is_not_detected(text):
    assert is_arabic(text) is False


def test_generate_refusal_follows_the_question_language(monkeypatch):
    from chat.graph.nodes import generate as node

    ar = node.generate({"question": "ما هي ماجرة؟", "condensed": "ما هي ماجرة؟", "retrieved": []})
    en = node.generate({"question": "What is Majara?", "condensed": "What is Majara?", "retrieved": []})
    assert ar["refused"] and ar["answer"] == node.REFUSAL_AR
    assert en["refused"] and en["answer"] == node.REFUSAL


def test_generate_prompt_asks_for_the_question_language():
    from chat.graph.nodes.generate import PROMPT

    assert "same language as the question" in PROMPT


def test_out_of_scope_refusal_follows_the_question_language():
    from chat.graph import build

    ar = build._mark_refused({"question": "ما الطقس اليوم؟"})
    en = build._mark_refused({"question": "What's the weather?"})
    assert ar["answer"] == build.REFUSAL_OUT_OF_SCOPE_AR
    assert en["answer"] == build.REFUSAL_OUT_OF_SCOPE
    assert ar["refused"] and en["refused"]


def test_condense_prompt_forbids_translating():
    from chat.graph.nodes.condense import PROMPT

    assert "never translate" in PROMPT


# --- Arabic spellings of the site's names -------------------------------------

from chat.language import NAME_GLOSSARY, normalize_names  # noqa: E402


@pytest.mark.parametrize("text,expected", [
    ("ما هي ماجرة؟", "ما هي Majara؟"),
    ("ماذا فعل محمد في صيت؟", "ماذا فعل محمد في SEET؟"),
    ("ما هو مشروع كيرا؟", "ما هو مشروع Keyraa؟"),
    ("ماذا يعمل في ماجرة وفي صيت", "ماذا يعمل في Majara وفي SEET"),
    ("هل عمل بماجرة؟", "هل عمل ب Majara؟"),  # one-letter prefix is kept
    ("ما هي ماجارا؟", "ما هي Majara؟"),
    ("What is Majara?", "What is Majara?"),  # already Latin: untouched
    # Stacked prefixes: and-the, with-the, to-the, and-to-the
    ("عمل والماجرة", "عمل وال Majara"),
    ("عمل بالماجرة", "عمل بال Majara"),
    ("ذهب للماجرة", "ذهب لل Majara"),
    ("ذهب وللماجرة", "ذهب ولل Majara"),
])
def test_known_names_are_mapped_to_latin(text, expected):
    assert normalize_names(text) == expected


@pytest.mark.parametrize("text", [
    "ماذا ماجرى في الاجتماع؟",  # "what happened": looks like ماجرة, is not
    "أين تقع المجرة؟",  # "the galaxy"
    "ما ماجرا الفيلم؟",  # "the film's incident": ماجرا is an ordinary word
    "كم سيت في الطاولة؟",  # سيت ("set") is an ordinary word
    "",
])
def test_look_alike_arabic_words_are_left_alone(text):
    assert normalize_names(text) == text


def test_the_glossary_names_all_three():
    for name in ("Majara", "SEET", "Keyraa"):
        assert name in NAME_GLOSSARY


def test_prompts_carry_the_glossary():
    from chat.graph.nodes import condense, generate, relevance

    for module in (condense, generate, relevance):
        assert "{glossary}" in module.PROMPT
