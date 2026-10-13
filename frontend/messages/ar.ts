import type { Messages } from "./en";

/** Arabic UI copy in clear, modern Standard Arabic (فصحى معاصرة), the register of
    Saudi company sites and professional profiles: first person where Mohammed
    speaks, metadata in third person. Only ask.greeting and ask.seeds keep a light
    Saudi tone, to match the chat's dialect answers. Tech terms use the established
    Arabic word, with the English in brackets where it isn't widely known. Typed
    against the English dictionary. Majara is مجرة; Keyraa and tool names stay in
    Latin letters. */
export const ar: Messages = {
  meta: {
    title: "محمد الأنصاري",
    description:
      "محمد الأنصاري — مهندس منتجات في مجرة، وطالب في تخصص نظم المعلومات بجامعة الملك سعود، يطوّر أنظمة الواجهة الخلفية (Backend) وخطوط معالجة البيانات وتطبيقات مدعومة بالذكاء الاصطناعي.",
    ogAlt: "محمد الأنصاري — مهندس منتجات في مجرة",
  },
  theme: {
    system: "التلقائي",
    light: "الفاتح",
    dark: "الداكن",
    aria: "المظهر: الوضع {current}. التبديل إلى الوضع {next}.",
  },
  lang: {
    switchAria: "التبديل إلى الإنجليزية",
  },
  hero: {
    monogram: "MA",
    nameFirst: "محمد",
    nameLast: "الأنصاري",
    fields: [
      { label: "الوظيفة", value: "مهندس منتجات في مجرة" },
      { label: "التخصص", value: "نظم المعلومات، جامعة الملك سعود" },
      { label: "الموقع", value: "الرياض، المملكة العربية السعودية" },
    ],
    tagline:
      "أدرس نظم المعلومات في جامعة الملك سعود، وأطوّر أنظمة الواجهة الخلفية (Backend) وخطوط معالجة البيانات وتطبيقات مدعومة بالذكاء الاصطناعي.",
    cta: "استعرض أعمالي",
  },
  about: {
    label: "نبذة عني",
    intro:
      "أطوّر برمجيات متكاملة (Full-stack) بدءًا من فهم المشكلة، وأحوّل الأفكار والاحتياجات الواقعية إلى منتجات يستخدمها الناس فعلًا.",
    quote:
      "ليس السؤال «كيف نبنيه؟» فحسب، بل «ما أهميته؟» و«مَن يستفيد منه؟»",
    body:
      "أنطلق في عملي من المتطلبات: أصوغ احتياجات الأعمال في صورة متطلبات منظّمة، وأبني نماذج أولية بسرعة وأحسّنها مرة بعد أخرى حتى تتحول الفكرة إلى برنامج يعمل فعليًا. كما أستكشف الذكاء الاصطناعي وأنظمة الوكلاء الذكية (Agentic AI) من خلال مشاريع عملية.",
  },
  work: {
    builtWith: "الأدوات المستخدمة",
    pickTool: "اختر أداة لترى أين استُخدمت",
    toolMatch: "استُخدمت {tool} في {count} من أصل {total}",
    cited: "استندت الإجابة إلى {count} من أصل {total}",
    clear: "مسح",
    experience: "الخبرة",
    projects: "المشاريع",
    previousProject: "المشروع السابق",
    nextProject: "المشروع التالي",
    onGithub: "{title} على GitHub",
    viewOnGithub: "عرض على GitHub",
  },
  ask: {
    label: "المحادثة الذكية",
    heading: "اسأل مساعدي الذكي عن أعمالي.",
    intro:
      "مساعد محادثة ذكي يستمد إجاباته مما كتبته عن خبراتي ومشاريعي والأدوات التي أستخدمها. اكتب سؤالك، أو اختر أحد الأسئلة المقترحة.",
    assistantName: "مساعد محمد الذكي",
    assistantTagline: "يعمل بالذكاء الاصطناعي · يجيب من ملف أعمال محمد فقط",
    greeting:
      "هلا! أنا مساعد ذكي مبني على ملف أعمال محمد. تفضّل، اسألني عن شغله.",
    seeds: [
      "وش سوّى في مجرة؟",
      "وش هو مشروع Keyraa؟",
      "هو متاح للعمل؟",
    ],
    inputLabel: "اطرح سؤالًا عن أعمال محمد",
    placeholder: "اسأل عن أعماله…",
    send: "إرسال السؤال",
    disclaimer:
      "تستند الإجابات إلى ما كتبه محمد عن أعماله فقط، ويعتذر المساعد عن أي سؤال خارج هذا النطاق.",
    thinking: "جارٍ التفكير…",
    sources: "المصادر",
    tryAgain: "إعادة المحاولة",
    errors: {
      throttled: "عدد الأسئلة كبير حاليًا. يُرجى المحاولة بعد دقيقة.",
      server: "حدث خطأ في خدمة المساعد. يُرجى المحاولة بعد قليل.",
      network: "تعذّر الاتصال بخدمة المساعد.",
      malformed: "وصل ردّ غير متوقع من خدمة المساعد.",
      unconfigured: "خدمة المساعد غير مُعدّة في هذه النسخة من الموقع.",
    },
  },
  contact: {
    label: "تواصل معي",
    heading:
      "إذا وجدت في أعمالي ما يرتبط بما تعمل عليه، فسيسعدني أن تحدّثني عنه.",
    email: "البريد الإلكتروني",
    github: "GitHub",
    linkedin: "LinkedIn",
    footer: "محمد الأنصاري — 2026",
  },
};
