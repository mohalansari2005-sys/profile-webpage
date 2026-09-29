# Fix: Arabic "What is Majara?" answered the wrong question

## Symptom
Asked "ما هي ماجرة؟" ("What is Majara?"), the chat answered a different question and rendered the name wrongly. Reported after `feat/chat-arabic` shipped.

## Causes found by reading the pipeline (not reproduced live: no API key on the dev machine)
1. `condense` was skipped on first turns, so the raw Arabic string was embedded and used to search an **English** corpus. "ماجرة" is a transliteration, not a word; cross-lingual embedding of it lands nowhere near "Majara", so unrelated records were retrieved and `generate` answered from them.
2. No node knew what "ماجرة" refers to, so a model could read it as a look-alike Arabic word.

## Fix
- `chat/language.py::normalize_names`: deterministic map of the known Arabic spellings (ماجرة/ماجرا/ماجارا -> Majara, صيت/سيت -> SEET, كيرا/كايرا -> Keyraa), keeping a one-letter prefix, applied to the question before any node reads it. Look-alikes (ماجرى "what happened", المجرة "the galaxy") are left alone by Arabic-letter boundaries.
- `condense` now runs for an Arabic question even with no history, and also returns `english_query` (the question in English, names in Latin). It is stored as `search_query`; `retrieve` embeds `search_query or condensed`. `condensed` stays in the user's language, so `generate` still answers in it. Failure falls back to the normalized question.
- `NAME_GLOSSARY` in the `condense`, `relevance` and `generate` prompts, so a spelling not in the table is still recognised.
- Cost: one extra fast-model (nano) call, only for Arabic questions.

## Tests
Offline: name mapping and look-alikes, Arabic condense path + fallback, English first turn still makes no call, retrieval uses `search_query`, glossary present in all three prompts.

## Not verified
Real embeddings and model behaviour. After deploy, ask the live chat "ما هي ماجرة؟" and check that the answer is about Majara and the source chip is Majara's record.
