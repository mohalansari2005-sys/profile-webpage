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
  /** Live site. Optional; it renders as the card's external-link icon. */
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
  { id: "web-scraping", label: "Web scraping", group: "Build" },
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
  { id: "postgis", label: "PostGIS", group: "Data & infrastructure" },
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
    title: "Product Engineer Intern",
    org: "Majara — Riyadh, hybrid",
    period: "Dec 2025 — Present",
    summary: "Product engineer intern on Wakil, Majara's property management platform, working in a multi-person engineering team. I took Customer 360 end to end, from product definition to shipped code, and work across the full stack in Django REST Framework and React with TypeScript.",
    tools: ["python", "javascript", "django", "react", "typescript", "playwright", "rest-apis", "full-stack", "systems-analysis", "agile", "sdlc", "b2b"],
    ar: { title: "متدرب مهندس منتجات", org: "مجرة — الرياض، عمل هجين", period: "ديسمبر 2025 — الآن", summary: "متدرب مهندس منتجات على منصة وكيل لإدارة العقارات التابعة لمجرة، ضمن فريق هندسي من عدة مهندسين. تولّيت ميزة Customer 360 من تعريف المنتج حتى الشيفرة المنشورة، وأعمل على المنصة بكامل مكوّناتها (Full-stack) باستخدام Django REST Framework وReact مع TypeScript." },
  },
  {
    id: "exp-seet",
    title: "Business Development Intern",
    org: "SEET (صيت) — marketing solutions agency, Riyadh",
    period: "Feb — Apr 2025",
    summary: "Worked backward from client objectives to concrete proposals — client meetings, sales pitches, and ongoing relationships. It taught me to translate a loosely defined problem into a solution that's actually useful and deliverable, the same skill that scopes a good engineering requirement.",
    tools: [],
    ar: { title: "متدرب في تطوير الأعمال", org: "صيت — وكالة حلول تسويقية، الرياض", period: "فبراير — أبريل 2025", summary: "كنت أنطلق من أهداف العملاء لأصل إلى مقترحات ملموسة، من خلال الاجتماعات معهم، وعروض المبيعات، وبناء علاقات مستمرة. وعلّمتني هذه التجربة كيف أحوّل مشكلة غير محددة المعالم إلى حل مفيد فعلًا وقابل للتنفيذ، وهي المهارة نفسها التي يقوم عليها تحديد المتطلبات الهندسية الجيدة." },
  },
];

export const projects: WorkRecord[] = [
  {
    id: "proj-home-finder",
    title: "Home Finder",
    org: "Personal project",
    period: "2026",
    summary: "Our search for a family home in Riyadh meant scrolling Aqar and Haraj daily: the same villa from three brokers, sizes buried in ad text, guessing the school run, and forgetting what we had rejected and why. So I built a private, Arabic-first app to do the tedious part. It merges listings, fills gaps in ads with an LLM, and scores each home 0–100 against our priorities, with reasons. It adds rush-hour drive times, learns from what we save and reject, plans visit days by district, and takes requests in plain Arabic through a LangGraph assistant.",
    tools: ["python", "fastapi", "sqlalchemy", "web-scraping", "react", "typescript", "tailwind", "langgraph", "openai-api", "postgres", "postgis", "docker", "pytest", "playwright", "github-actions"],
    href: "https://home.alansari.stream",
    repo: "https://github.com/mohalansari2005-sys/home-finder",
    ar: { title: "بيتنا", org: "مشروع شخصي", summary: "كان بحث عائلتي عن منزل نشتريه في الرياض عبئًا يوميًا: تصفّحٌ متواصل لعقار وحراج، والمنزل نفسه يعرضه أكثر من وسيط، ومساحته وعمره مخفيّان في نص الإعلان، وزمن الطريق إلى المدرسة صباحًا مجرد تخمين، ثم يضيع علينا ما استبعدناه ولماذا. فبنيت تطبيقًا خاصًا بالعربية يتولّى هذا العناء عنّا: يجمع الإعلانات ويدمج المكرر منها، ويستكمل بياناتها الناقصة بنموذج لغوي، ويمنح كل منزل درجة من 100 وفق أولوياتنا مع بيان أسبابها. ويحسب زمن الوصول في ساعات الذروة، ويعدّل أوزان التقييم بحسب ما نحفظه ونستبعده، وينظّم جولات المعاينة حسب الأحياء. ويضم مساعدًا ذكيًا مبنيًا بـLangGraph يعدّل معايير البحث ويقترح المنازل من طلباتنا بلغتنا اليومية." },
  },
  {
    id: "proj-keyraa",
    title: "Keyraa",
    org: "Majara",
    period: "2026",
    summary: "Keyraa, a corporate hotel booking platform: a FastAPI backend that turns bulk employee trip requests into booked hotels — Amadeus search, bulk booking through Celery workers, and confirmation emails. I built the core flows solo: multi-tenant, idempotent, with retry and backoff around a rate-limited external API. Shelved before launch when industry regulations changed.",
    tools: ["python", "fastapi", "sqlalchemy", "postgres", "redis", "celery", "docker", "rest-apis", "pytest"],
    repo: "https://github.com/mohalansari2005-sys/keyraa-hotel-booking",
    ar: { org: "مجرة", summary: "منصة Keyraa لحجز الفنادق للشركات: واجهة خلفية مبنية بـFastAPI تحوّل طلبات السفر الجماعية للموظفين إلى حجوزات فندقية مؤكدة، وتشمل البحث في Amadeus، والحجز الجماعي عبر مهام Celery الخلفية، ورسائل التأكيد بالبريد الإلكتروني. طوّرت مسارات العمل الأساسية بمفردي، مع دعم تعدد المستأجرين (Multi-tenancy)، ومنع تكرار العمليات عند إعادة تنفيذها (Idempotency)، وإعادة المحاولة بفواصل زمنية متزايدة عند التعامل مع واجهة API خارجية تفرض حدًّا لعدد الطلبات. وأُوقف المشروع قبل إطلاقه إثر تغيّر اللوائح التنظيمية في القطاع." },
  },
  {
    id: "proj-profile-webpage",
    title: "Portfolio website with an AI chat",
    org: "Personal project",
    period: "2026",
    summary: "This website: a statically exported Next.js and TypeScript front end whose content is a validated Markdown corpus, plus a Django and LangGraph chatbot that answers questions about my work by retrieving over pgvector with OpenAI models, and refuses anything it cannot ground in that corpus. English and Arabic (right-to-left), dark mode, CI with Playwright, and a backend that deploys itself to a VPS.",
    tools: ["typescript", "react", "nextjs", "tailwind", "python", "django", "langgraph", "openai-api", "rag", "postgres", "pgvector", "redis", "docker", "pytest", "playwright", "github-actions"],
    repo: "https://github.com/mohalansari2005-sys/profile-webpage",
    ar: { title: "موقعي الشخصي مع مساعد ذكي", org: "مشروع شخصي", summary: "هذا الموقع نفسه: واجهة أمامية مبنية بـNext.js وTypeScript تُولَّد مسبقًا على هيئة ملفات ثابتة، ويُستمد محتواها من ملفات Markdown يُتحقَّق من صحتها آليًا، ويرافقها مساعد محادثة ذكي مبني بـDjango وLangGraph يجيب عن الأسئلة المتعلقة بأعمالي مستعينًا بالاسترجاع من pgvector ونماذج OpenAI، ويرفض أي سؤال لا يجد له سندًا في هذا المحتوى. يتوفر الموقع بالعربية (من اليمين إلى اليسار) والإنجليزية، ويدعم الوضع الداكن، مع تكامل مستمر (CI) يشغّل اختبارات Playwright، وواجهة خلفية تُنشر تلقائيًا على خادم VPS." },
  },
];

/** The records the chat can cite that have no row on the page (the about and
    faq records). Only their titles ship, for the answer's source chips. */
export const offPageRecords: Pick<WorkRecord, "id" | "title" | "ar">[] = [
  { id: "about-bio", title: "About", ar: { title: "نبذة عني" } },
  { id: "about-education", title: "Education", ar: { title: "التعليم" } },
  { id: "faq-availability", title: "Are you available for work?", ar: { title: "هل أنت متاح للعمل؟" } },
];

export const toolById = new Map(tools.map((tool) => [tool.id, tool]));
