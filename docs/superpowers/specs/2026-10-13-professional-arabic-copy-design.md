# The Arabic page in professional Modern Standard Arabic

## Why
The owner found the Arabic page read like a literal translation of the English, with some words inaccurate and some unprofessional. Two causes: the dialect pass (`2026-09-30-saudi-dialect-copy-design.md`) put the whole page in spoken Saudi (شغلي، مكاني، شوف، بروحي، الحين، زينة، هالمحتوى، ينتحقق، تنبني، الإيميل), and several technical phrases were calques (خلفية FastAPI for "backend", عمّال Celery for "workers", تراجع for "backoff", برامج متكاملة for "full-stack", خدمة الإجابة, روبوت دردشة, الأنظمة الوكيلة, «شوف وين يتقاطع الشغل», «ما تتكرر فيها العمليات بالغلط» for "idempotent", أنظمة القطاع for "regulations"). This supersedes the dialect spec for the page copy; the chat's generated answers stay in Saudi dialect.

## What
- **`frontend/messages/ar.ts` rewritten** in clear modern Standard Arabic (the register of Saudi company sites and professional profiles), first person where Mohammed speaks, metadata in third person. Buttons use verbal nouns (إرسال السؤال، إعادة المحاولة، عرض على GitHub، التبديل إلى الإنجليزية); errors use تعذّر / يُرجى. Theme names became الوضع التلقائي / الفاتح / الداكن so they read grammatically inside the aria template.
- **Only `ask.greeting` and `ask.seeds` keep a light Saudi tone** (هلا!، وش سوّى في مجرة؟), because they sit in the chat, whose answers are in dialect. The seed still names مجرة bare, so the backend reads it as Majara, not "galaxy".
- **Content `*_ar` fields** (Majara, SEET, Keyraa, this website) rewritten in the same register, conveying the English bodies rather than translating word for word.
- **Technical terms:** the established Arabic term, with the English in brackets only where the Arabic isn't widely known: الواجهة الخلفية (Backend)، برمجيات متكاملة (Full-stack)، أنظمة الوكلاء الذكية (Agentic AI)، تعدد المستأجرين (Multi-tenancy)، منع تكرار العمليات عند إعادة تنفيذها (Idempotency)، تكامل مستمر (CI). Product and tool names stay in Latin letters.
- `frontend/lib/content.ts` regenerated; `backend/corpus.json` is unchanged (Arabic never reaches it).

## Decisions to flag
- The major is written **نظم المعلومات** (the owner's choice), so the Arabic no longer mirrors the English "Computer Information Systems". `content/about/education.md` already says "Information Systems".
- The Majara period reads «نوفمبر 2025 — الآن»: «حتى الآن» wrapped onto a second line in the date column from 640px up.
- The sticky tool bar's status lines lead with the count («2 من أصل 4 تستخدم Docker»), like the English: the line truncates at the end on a 320px phone, so the numbers must come first. The verb agrees with the implied works, not with the tool name. The bar's heading stays the short «الأدوات» for the same reason.
- The hero's location label is «المدينة», not «الموقع», which on a website also reads as "the site".
- Skill chips (Full-stack, Systems analysis, B2B software…) stay English, by the owner's choice.
- The backend's fixed Arabic refusals (`REFUSAL_AR`, `REFUSAL_OUT_OF_SCOPE_AR`) are unchanged and remain in dialect, consistent with the chat's answers.

## Tests
No test edits: `e2e/i18n.spec.ts` reads `messages/ar.ts` and `lib/content`. Content tests (37), `content:check`, lint, `tsc --noEmit`, static build, and the full Playwright suite (104). Manual screenshots of `/ar` at 320, 640, 768, 1024 and 1280px in light and dark: no horizontal overflow, «البريد الإلكتروني» stays on one line in the contact label column, the theme toggle reads «المظهر: الوضع التلقائي. التبديل إلى الوضع الفاتح.».

## Not verified
A native reader's final judgement of tone and word choice: the owner should proofread every string in `ar.ts` and the `*_ar` fields.
