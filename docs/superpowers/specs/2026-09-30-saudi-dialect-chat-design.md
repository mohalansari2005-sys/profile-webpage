# Chat answers in Saudi white dialect; Majara is "مجرة"

## Why
Arabic answers read as translated Modern Standard Arabic (فصحى). The owner wants the chatbot to answer Arabic questions in Saudi white dialect (اللهجة البيضاء, leaning Najdi), and corrected the company name: in Arabic, Majara is "مجرة" (typed "مجره"), not "ماجرة".

## What
- **Dialect instruction, only for Arabic questions.** `generate.py` gains `ARABIC_STYLE`, inserted into the prompt when `is_arabic(state["question"])` (the visitor's own words, not the condensed rewrite, so a follow-up like "وش سوّى هناك؟" still gets it). It asks for natural spoken Saudi Arabic, explicitly *not* فصحى, with everyday forms (وش, ليش, مين, الحين, أبغى, مو, اللي, لين, شغل, زين, سوّى), no heavy slang or vulgarity, professional, third person about Mohammed. English questions get no dialect text (tested).
- **Names in Arabic answers:** Majara is written مجرة and SEET صيت; Keyraa and tool names stay in Latin. The base language rule now defers to the style notes so the two never contradict.
- **Refusals** (`REFUSAL_AR`, `REFUSAL_OUT_OF_SCOPE_AR`) rewritten in the same voice ("أجاوب بس…", not "أجيب فقط…").
- **Majara's spelling.** `NAME_ALIASES` keeps the old "ماجرة" family (and adds "ماجره"); new `AMBIGUOUS_ALIASES` maps "مجرة" / "مجره" to Majara. Because "مجرة" is also the ordinary Arabic word for **galaxy**, it is read as the company only as a bare proper noun: no definite article and no "lil-" ("المجرة", "للمجرة" stay galaxy), at most a one-letter and/in/for prefix ("في مجرة", "بمجرة", "ولمجرة"). The prompt glossary says the same, so a spelling outside the table is still understood.
- The relevance prompt now says the message may be in any Arabic dialect.
- Live-eval questions use the new spelling and colloquial phrasing ("وش هي مجره؟", "وش سوّى محمد في صيت؟").

## Tests (offline, 135 pass)
Spellings ("ما هي مجرة؟", "في مجره", "بمجرة", old "ماجره"); galaxy sentences left alone ("أين تقع المجرة؟", "ما هي المجرة؟", "كم عدد نجوم المجرة؟", "ذهب للمجرة"); the Arabic prompt carries the dialect and the Arabic company names, the English prompt carries none; the dialect keys off the original question; refusals are colloquial.

## Not verified
How the model actually writes: no OpenAI key on the dev machine, so the tone of real answers and the 4 new/updated live evals were not run. After deploy, ask in Arabic ("وش هي مجرة؟") and check the reply is colloquial Saudi, names مجرة, and answers the right question. If the register is off (too Egyptian/Levantine, too formal, too slangy), send me the reply and I'll tune `ARABIC_STYLE`.
