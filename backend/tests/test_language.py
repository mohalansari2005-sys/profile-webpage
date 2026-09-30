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
    # The current spelling, with ة or the ه people type on a phone
    ("ما هي مجرة؟", "ما هي Majara؟"),
    ("وش سوّى محمد في مجره؟", "وش سوّى محمد في Majara؟"),
    ("هل اشتغل بمجرة؟", "هل اشتغل ب Majara؟"),
    ("وش هي ماجره؟", "وش هي Majara؟"),  # old spelling, ه
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
    # مجرة is also the ordinary word "galaxy": only a bare proper noun is Majara
    "أين تقع المجرة؟",
    "ما هي المجرة؟",
    "كم عدد نجوم المجرة؟",
    "ذهب للمجرة",
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


# --- Saudi white dialect for Arabic questions -----------------------------------

def _captured_prompt(monkeypatch, question):
    from chat.graph.nodes import generate as node

    seen = {}

    def fake(prompt, schema, *, fast=False):
        seen["prompt"] = prompt
        return node.Answer(answer="a", used_chunk_ids=[], sufficient=False), {}

    monkeypatch.setattr(node, "structured", fake)
    node.generate({
        "question": question, "condensed": question,
        "retrieved": [{"chunk_id": "c#s", "record_id": "c", "title": "t", "text": "x"}],
    })
    return seen["prompt"]


def test_an_arabic_question_asks_for_saudi_white_dialect(monkeypatch):
    prompt = _captured_prompt(monkeypatch, "وش سوّى محمد في مجرة؟")
    assert "Saudi white dialect" in prompt
    assert "Modern Standard Arabic" in prompt  # told NOT to use it
    assert "Majara is مجرة" in prompt  # company written in Arabic script


def test_an_english_question_gets_no_dialect_instruction(monkeypatch):
    prompt = _captured_prompt(monkeypatch, "What did he build at Majara?")
    assert "Saudi" not in prompt
    assert "Style for this Arabic answer" not in prompt


def test_the_dialect_follows_the_original_question_not_the_rewrite(monkeypatch):
    """A follow-up is condensed to a standalone question; the dialect must key off
    what the visitor actually wrote."""
    from chat.graph.nodes import generate as node

    seen = {}
    monkeypatch.setattr(node, "structured", lambda prompt, *a, **k: (
        seen.setdefault("p", prompt) and None, {}))
    node.generate({
        "question": "وش سوّى هناك؟", "condensed": "What did he build at Majara?",
        "retrieved": [{"chunk_id": "c#s", "record_id": "c", "title": "t", "text": "x"}],
    })
    assert "Saudi white dialect" in seen["p"]


def test_the_arabic_refusals_are_colloquial_not_formal():
    from chat.graph import build
    from chat.graph.nodes import generate as node

    for text in (node.REFUSAL_AR, build.REFUSAL_OUT_OF_SCOPE_AR):
        assert "أجاوب" in text  # spoken "I answer", not the formal "أجيب"
        assert "أجيب" not in text
    assert "مجرة" in NAME_GLOSSARY and "galaxy" in NAME_GLOSSARY
