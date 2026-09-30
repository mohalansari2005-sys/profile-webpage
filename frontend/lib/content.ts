/**
 * GENERATED FILE — DO NOT EDIT.
 *
 * Written by scripts/build-content.mjs from the markdown corpus in content/.
 * Edit the corpus, then run `npm run content` from the repo root.
 *
 * Only the fields the page renders live here. Each record's body prose stays
 * in content/ and is read by the chat backend's ingestion, never shipped to
 * the browser.
 */

export type ToolGroup = "Build" | "Data & infrastructure" | "Practice";

export const toolGroups: ToolGroup[] = ["Build", "Data & infrastructure", "Practice"];

export type Tool = {
  id: string;
  label: string;
  group: ToolGroup;
};

export type WorkRecord = {
  id: string;
  title: string;
  org: string;
  period: string;
  summary: string;
  tools: string[];
  href?: string;
  /** GitHub repository. Every project should have one; it renders as the
      card's GitHub icon link. */
  repo?: string;
  /** Arabic display copy for /ar; any field missing falls back to English. */
  ar?: { title?: string; org?: string; period?: string; summary?: string };
};

export const tools: Tool[] = [
  { id: "python", label: "Python", group: "Build" },
  { id: "javascript", label: "JavaScript", group: "Build" },
  { id: "fastapi", label: "FastAPI", group: "Build" },
  { id: "sqlalchemy", label: "SQLAlchemy", group: "Build" },
  { id: "rest-apis", label: "REST APIs", group: "Build" },
  { id: "full-stack", label: "Full-stack", group: "Build" },
  { id: "typescript", label: "TypeScript", group: "Build" },
  { id: "react", label: "React", group: "Build" },
  { id: "nextjs", label: "Next.js", group: "Build" },
  { id: "tailwind", label: "Tailwind CSS", group: "Build" },
  { id: "django", label: "Django", group: "Build" },
  { id: "openai-api", label: "OpenAI API", group: "Build" },
  { id: "langgraph", label: "LangGraph", group: "Build" },
  { id: "rag", label: "RAG", group: "Build" },
  { id: "postgres", label: "PostgreSQL", group: "Data & infrastructure" },
  { id: "redis", label: "Redis", group: "Data & infrastructure" },
  { id: "celery", label: "Celery", group: "Data & infrastructure" },
  { id: "docker", label: "Docker", group: "Data & infrastructure" },
  { id: "pytest", label: "pytest", group: "Data & infrastructure" },
  { id: "pgvector", label: "pgvector", group: "Data & infrastructure" },
  { id: "playwright", label: "Playwright", group: "Data & infrastructure" },
  { id: "github-actions", label: "GitHub Actions", group: "Data & infrastructure" },
  { id: "systems-analysis", label: "Systems analysis", group: "Practice" },
  { id: "agile", label: "Agile", group: "Practice" },
  { id: "sdlc", label: "SDLC", group: "Practice" },
  { id: "b2b", label: "B2B software", group: "Practice" },
];

export const experience: WorkRecord[] = [
  {
    id: "exp-majara",
    title: "Product Engineering Intern",
    org: "Majara — Riyadh, hybrid",
    period: "Nov 2025 — Present",
    summary: "Worked across full-stack development and product development, translating requirements and functional needs into prototypes and product features from concept through to working software.",
    tools: ["python", "javascript", "rest-apis", "full-stack", "systems-analysis", "agile", "sdlc", "b2b"],
    ar: { title: "متدرب هندسة منتجات", org: "مجرة — الرياض، شغل هجين", period: "نوفمبر 2025 — الحين", summary: "اشتغلت على تطوير البرامج المتكاملة وتطوير المنتجات، وكنت أحوّل المتطلبات والاحتياجات الوظيفية إلى نماذج أولية وميزات للمنتج، من الفكرة لين تصير برنامج شغّال." },
  },
  {
    id: "exp-seet",
    title: "Business Development Intern",
    org: "SEET (صيت) — marketing solutions agency, Riyadh",
    period: "Feb — Apr 2025",
    summary: "Worked backward from client objectives to concrete proposals — client meetings, sales pitches, and ongoing relationships. It taught me to translate a loosely defined problem into a solution that's actually useful and deliverable, the same skill that scopes a good engineering requirement.",
    tools: [],
    ar: { title: "متدرب تطوير أعمال", org: "صيت — وكالة حلول تسويقية، الرياض", period: "فبراير — أبريل 2025", summary: "كنت أبدأ من أهداف العميل وأوصل لمقترحات واضحة: اجتماعات مع العملاء وعروض مبيعات وعلاقات مستمرة. وتعلمت منها كيف أحوّل مشكلة مو محددة لحل مفيد وقابل للتسليم، وهي نفس المهارة اللي تطلّع متطلبات هندسية زينة." },
  },
];

export const projects: WorkRecord[] = [
  {
    id: "proj-keyraa",
    title: "Keyraa",
    org: "Majara",
    period: "2026",
    summary: "Keyraa, a corporate hotel booking platform: a FastAPI backend that turns bulk employee trip requests into booked hotels — Amadeus search, bulk booking through Celery workers, and confirmation emails. I built the core flows solo: multi-tenant, idempotent, with retry and backoff around a rate-limited external API. Shelved before launch when industry regulations changed.",
    tools: ["python", "fastapi", "sqlalchemy", "postgres", "redis", "celery", "docker", "rest-apis", "pytest"],
    repo: "https://github.com/mohalansari2005-sys/keyraa-hotel-booking",
    ar: { org: "مجرة", summary: "Keyraa منصة حجز فنادق للشركات: خلفية FastAPI تحوّل طلبات سفر الموظفين الجماعية إلى حجوزات فنادق مؤكدة، عن طريق بحث Amadeus والحجز الجماعي بعمّال Celery ورسائل التأكيد بالإيميل. بنيت الأجزاء الأساسية بروحي: متعددة المستأجرين وما تتكرر فيها العمليات بالغلط، مع إعادة محاولة وتراجع حول واجهة خارجية لها حد على الطلبات. وقفنا المشروع قبل الإطلاق لأن أنظمة القطاع تغيّرت." },
  },
  {
    id: "proj-profile-webpage",
    title: "Portfolio website with an AI chat",
    org: "Personal project",
    period: "2026",
    summary: "This website: a statically exported Next.js and TypeScript front end whose content is a validated Markdown corpus, plus a Django and LangGraph chatbot that answers questions about my work by retrieving over pgvector with OpenAI models, and refuses anything it cannot ground in that corpus. English and Arabic (right-to-left), dark mode, CI with Playwright, and a backend that deploys itself to a VPS.",
    tools: ["typescript", "react", "nextjs", "tailwind", "python", "django", "langgraph", "openai-api", "rag", "postgres", "pgvector", "redis", "docker", "pytest", "playwright", "github-actions"],
    repo: "https://github.com/mohalansari2005-sys/profile-webpage",
    ar: { title: "موقعي الشخصي مع دردشة ذكية", org: "مشروع شخصي", summary: "هذا الموقع: واجهة Next.js وTypeScript تنبني كملفات ثابتة، ومحتواها ملفات Markdown ينتحقق منها، ومعها روبوت دردشة بـDjango وLangGraph يجاوب عن شغلي بالبحث في pgvector ونماذج OpenAI، ويرفض أي سؤال ما يقدر يثبته من هالمحتوى. عربي وإنجليزي (من اليمين لليسار)، ووضع داكن، واختبارات آلية بـPlaywright، والخلفية تنشر نفسها على سيرفر VPS." },
  },
];

export const toolById = new Map(tools.map((tool) => [tool.id, tool]));
