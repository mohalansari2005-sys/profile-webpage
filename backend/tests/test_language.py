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
