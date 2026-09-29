# Chat answers in Arabic

## Why
Visitors who ask in Arabic should get an Arabic answer. Nothing in the pipeline handled language: the prompts were English-only, and both hard-coded refusals were English, so an Arabic visitor who was refused saw English.

## What
Backend only (`backend/chat/`). The corpus stays English; `text-embedding-3-small` retrieves across languages, and whole-record expansion over a handful of records makes a miss unlikely.

- `generate` PROMPT: answer in the same language as the question; keep names (Majara, SEET, Keyraa, tool names) in Latin spelling.
- `condense` PROMPT: keep the latest message's language, never translate it.
- `relevance` PROMPT: the message may be in any language; Arabic-script names (ماجرة, صيت) are treated like their Latin spelling.
- Refusals: `REFUSAL_AR` (generate) and `REFUSAL_OUT_OF_SCOPE_AR` (build), chosen by `chat/language.py::is_arabic(state["question"])`.
- `is_arabic` is deterministic: true when most *words* contain Arabic script. The out-of-scope path refuses before any generation, so no model call could report the language. Words, not letters, so "ما هي Majara؟" is Arabic while "What does صيت mean?" stays English.

## Tests
- Offline: `tests/test_language.py` (detection, both refusal paths, prompt wording).
- Live (`pytest -m eval`, opt-in, spends real API calls): 5 in-scope and 3 out-of-scope Arabic cases added to `tests/test_relevance_eval.py`.

## Not included
Translating the corpus, or a per-request `language` field in the API. Arabic UI copy is the separate `feat/i18n-rtl` branch.
