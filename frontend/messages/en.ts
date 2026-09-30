/** English UI copy. `ar.ts` is typed against this file, so a key missing there
    fails the typecheck. Placeholders like {tool} are filled by `format()`. */
export const en = {
  meta: {
    title: "Mohammed Alansari",
    description:
      "Mohammed Alansari — Product Engineer at Majara and Computer Information Systems student at King Saud University, building backend systems, data pipelines, and AI-enabled applications.",
    ogAlt: "Mohammed Alansari — Product Engineer at Majara",
  },
  theme: {
    system: "System",
    light: "Light",
    dark: "Dark",
    aria: "Theme: {current}. Switch to {next}.",
  },
  lang: {
    switchAria: "Switch to Arabic",
  },
  hero: {
    monogram: "MA",
    nameFirst: "Mohammed",
    nameLast: "Alansari",
    fields: [
      { label: "Role", value: "Product Engineer at Majara" },
      { label: "Focus", value: "Computer Information Systems, King Saud University" },
      { label: "Based", value: "Riyadh, Saudi Arabia" },
    ],
    tagline:
      "Computer Information Systems student at King Saud University, building backend systems, data pipelines, and AI-enabled applications.",
    cta: "See where the work connects",
  },
  about: {
    label: "About",
    intro:
      "I build full-stack software from the problem up, turning ideas and real-world needs into products people can actually use.",
    quote:
      "Not just “How do we build this?” but “Why does it matter?” and “Who does it help?”",
    body:
      "I work from the requirements up, translating business needs into structured requirements, and rapidly prototyping and iterating until the idea becomes working software. I also explore AI and agentic systems through hands-on projects.",
  },
  work: {
    builtWith: "Built with",
    pickTool: "Pick a tool to see where it was used",
    toolMatch: "{count} of {total} use {tool}",
    cited: "{count} of {total} cited in the answer",
    clear: "Clear",
    experience: "Experience",
    projects: "Projects",
    previousProject: "Previous project",
    nextProject: "Next project",
    onGithub: "{title} on GitHub",
    viewOnGithub: "View on GitHub",
  },
  ask: {
    label: "AI chat",
    heading: "Ask my AI assistant about my work.",
    intro:
      "A chatbot that answers from what I’ve written about my roles, projects and tools. Type a question, or tap a suggestion.",
    assistantName: "Mohammed’s AI assistant",
    assistantTagline: "AI chatbot · answers only from his portfolio",
    greeting:
      "Hi, I’m an AI chatbot trained on Mohammed’s portfolio. Ask me about his work.",
    seeds: [
      "What did he build at Majara?",
      "What is Keyraa?",
      "Is he available for work?",
    ],
    inputLabel: "Ask a question about Mohammed’s work",
    placeholder: "Ask about his work…",
    send: "Send question",
    disclaimer:
      "Answers come only from what Mohammed has written about his own work. Anything outside that, it declines.",
    thinking: "Thinking…",
    sources: "Sources",
    tryAgain: "Try again",
    errors: {
      throttled: "Too many questions right now — try again in a minute.",
      server: "The answer service hit an error. Try again in a moment.",
      network: "Couldn’t reach the answer service.",
      malformed: "The answer service sent back something unexpected.",
      unconfigured: "The answer service isn’t configured for this build.",
    },
  },
  contact: {
    label: "Contact",
    heading:
      "If any of this connects to what you’re building, I’d like to hear about it.",
    email: "Email",
    github: "GitHub",
    linkedin: "LinkedIn",
    footer: "Mohammed Alansari — 2026",
  },
};

export type Messages = typeof en;
