# The Arabic page in Saudi white dialect

## Why
The Arabic copy I first drafted was a literal, formal translation (فصحى). The owner wants the whole Arabic page in Saudi white dialect (اللهجة البيضاء, Najdi-leaning), the way a Saudi would actually say it, and Majara written مجرة, not ماجرة.

## What
- **`frontend/messages/ar.ts` rewritten** (UI, section text, chat interface, errors, contact) in spoken Saudi: وش / ليش / مين / الحين / مو / اللي / لين / أسوّي / زين / برا-style forms, first person, direct. Examples: the hero labels "شغلي / دراستي / مكاني" instead of "الدور / التخصص / الموقع"; "شوف وين يتقاطع الشغل"; the About quote "مو بس «كيف نبني هذا؟»، لكن «ليش يهم؟» و«مين يستفيد منه؟»"; chat greeting "هلا! أنا روبوت دردشة ذكي…"; errors "صار خطأ عند خدمة الإجابة. جرّب بعد شوي."; suggestion chips "وش سوّى في مجرة؟" / "هو متاح للشغل؟". "System" theme reads "حسب الجهاز" (follows the device), clearer than a literal "النظام". Metadata description stays in a cleaner register (it is a third-person summary for search and share cards).
- **Content `*_ar` fields** (Majara, SEET, Keyraa, and this-website records) rewritten in the same voice in first person ("اشتغلت على…", "بنيت الأجزاء الأساسية بروحي", "وقفنا المشروع…"), with مجرة for Majara and صيت for SEET; Keyraa and tool names stay Latin. Arabic content still never reaches `backend/corpus.json` (unchanged by this PR; tested).
- **Tests read the dictionaries instead of hard-coding Arabic.** `e2e/i18n.spec.ts` now imports `messages/ar.ts`, `lib/content` and `format`, so rewording the Arabic never needs a test edit; the tests check the right strings land in the right places. Only mock chat data stays literal.
- **Two citation-click tests hardened** (`chat.spec.ts`, `projects.spec.ts`): they passed 60/60 in isolation but failed once each in a fully saturated parallel run, most likely because the click landed while the chat box was still smooth-scrolling. They now retry click + focus together.

## Decisions to flag
- I chose the standard spelling **مجرة** (with ة) in the UI; the owner typed مجره. The backend accepts both. Change the string in `ar.ts` and the `*_ar` fields if the brand uses ه.
- The name "محمد الأنصاري" is unchanged; the owner has not confirmed the spelling.
- "White dialect" is a register, not a single accent: colloquial and clear to any Saudi, with Najdi-leaning forms, not thick slang. All copy is drafted for the owner's review.

## Tests
Full Playwright suite 103 tests x3 repeats (309 passed), content tests 37, lint, tsc.

## Not verified
A native reader's judgement of tone. This is the part that needs the owner's eyes.
