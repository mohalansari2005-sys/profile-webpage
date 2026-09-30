import type { Messages } from "./en";

/** Arabic UI copy in Saudi white dialect (اللهجة البيضاء, Najdi-leaning): the
    spoken register a Saudi reader finds natural, not Modern Standard Arabic.
    Typed against the English dictionary. Majara is مجرة; Keyraa and tool names
    stay in Latin letters. */
export const ar: Messages = {
  meta: {
    title: "محمد الأنصاري",
    description:
      "محمد الأنصاري — مهندس منتجات في مجرة وطالب نظم معلومات حاسوبية في جامعة الملك سعود، يبني أنظمة خلفية وخطوط بيانات وتطبيقات فيها ذكاء اصطناعي.",
    ogAlt: "محمد الأنصاري — مهندس منتجات في مجرة",
  },
  theme: {
    system: "حسب الجهاز",
    light: "فاتح",
    dark: "داكن",
    aria: "المظهر: {current}. غيّره إلى {next}.",
  },
  lang: {
    switchAria: "غيّر اللغة للإنجليزية",
  },
  hero: {
    monogram: "MA",
    nameFirst: "محمد",
    nameLast: "الأنصاري",
    fields: [
      { label: "شغلي", value: "مهندس منتجات في مجرة" },
      { label: "دراستي", value: "نظم المعلومات الحاسوبية، جامعة الملك سعود" },
      { label: "مكاني", value: "الرياض، السعودية" },
    ],
    tagline:
      "طالب نظم معلومات حاسوبية في جامعة الملك سعود، وأشتغل على الأنظمة الخلفية وخطوط البيانات والتطبيقات اللي فيها ذكاء اصطناعي.",
    cta: "شوف وين يتقاطع الشغل",
  },
  about: {
    label: "عني",
    intro:
      "أبني برامج متكاملة تبدأ من المشكلة نفسها، وأحوّل الأفكار واحتياجات الناس الحقيقية إلى منتجات يستفيدون منها فعلًا.",
    quote:
      "مو بس «كيف نبني هذا؟»، لكن «ليش يهم؟» و«مين يستفيد منه؟»",
    body:
      "أبدأ من المتطلبات: أحوّل احتياج العمل إلى متطلبات مرتبة، وأسوّي نماذج أولية بسرعة وأعدّل عليها لين تصير الفكرة برنامج شغّال. وأجرّب كذلك الذكاء الاصطناعي والأنظمة الوكيلة من خلال مشاريع عملية.",
  },
  work: {
    builtWith: "الأدوات",
    pickTool: "اختر أداة وشوف وين استخدمتها",
    toolMatch: "استخدمت {tool} في {count} من {total}",
    cited: "{count} من {total} مذكورة في الجواب",
    clear: "مسح",
    experience: "الخبرة",
    projects: "المشاريع",
    previousProject: "المشروع اللي قبله",
    nextProject: "المشروع اللي بعده",
    onGithub: "{title} على GitHub",
    viewOnGithub: "شوفه على GitHub",
  },
  ask: {
    label: "دردشة ذكية",
    heading: "اسأل مساعدي الذكي عن شغلي.",
    intro:
      "روبوت دردشة يجاوبك من اللي كتبته عن أدواري ومشاريعي والأدوات اللي أستخدمها. اكتب سؤالك أو اختر من الاقتراحات.",
    assistantName: "مساعد محمد الذكي",
    assistantTagline: "روبوت دردشة ذكي · يجاوب من ملفه المهني بس",
    greeting:
      "هلا! أنا روبوت دردشة ذكي مبني على ملف محمد المهني. اسألني عن شغله.",
    seeds: [
      "وش سوّى في مجرة؟",
      "وش هو مشروع Keyraa؟",
      "هو متاح للشغل؟",
    ],
    inputLabel: "اسأل عن شغل محمد",
    placeholder: "اسأل عن شغله…",
    send: "أرسل السؤال",
    disclaimer:
      "الإجابات تجي بس من اللي كتبه محمد عن شغله، وأي شي خارج هذا يعتذر عنه.",
    thinking: "لحظة، أفكر…",
    sources: "المصادر",
    tryAgain: "حاول مرة ثانية",
    errors: {
      throttled: "أسئلة كثيرة الحين، جرّب بعد دقيقة.",
      server: "صار خطأ عند خدمة الإجابة. جرّب بعد شوي.",
      network: "ما قدرت أوصل لخدمة الإجابة.",
      malformed: "خدمة الإجابة رجّعت شي غير متوقع.",
      unconfigured: "خدمة الإجابة مو مفعّلة في هذي النسخة.",
    },
  },
  contact: {
    label: "تواصل",
    heading: "لو شفت شي هنا يناسب اللي تشتغل عليه، يسعدني أسمع منك.",
    email: "الإيميل",
    github: "GitHub",
    linkedin: "LinkedIn",
    footer: "محمد الأنصاري — 2026",
  },
};
