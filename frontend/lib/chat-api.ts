/**
 * The browser's whole view of the chat backend.
 *
 * The only environment variable the frontend gets is the API's URL, which is
 * safe to inline into the bundle. The OpenAI key lives exclusively in the
 * Django container — that separation is the reason the backend exists, so
 * nothing in `frontend/` may ever read an OPENAI_* variable.
 */
export const CHAT_API_URL = process.env.NEXT_PUBLIC_CHAT_API_URL;

/** Mirrors the server's own cap. The server truncates again regardless. */
export const MAX_HISTORY = 6;

const TIMEOUT_MS = 30_000;

export type ChatMessage = { role: "user" | "assistant"; content: string };
export type ChatSource = { record_id: string; title: string };

export type ChatAnswer = {
  answer: string;
  sources: ChatSource[];
  refused: boolean;
};

export type ChatResult =
  | { ok: true; data: ChatAnswer }
  | { ok: false; error: ChatError };

/**
 * Why a request did not produce an answer. These are kinds, not sentences: the
 * UI turns each into copy in the reader's language (messages/*.ts). A refusal
 * is *not* one of these — a refusal is a successful, grounded "I can't answer
 * that from the corpus" and arrives as `ok: true`.
 */
export type ChatError =
  | "throttled"
  | "dailyCap"
  | "server"
  | "network"
  | "malformed"
  | "unconfigured";

function isSource(value: unknown): value is ChatSource {
  if (typeof value !== "object" || value === null) return false;
  const source = value as Record<string, unknown>;
  return (
    typeof source.record_id === "string" && typeof source.title === "string"
  );
}

/**
 * Narrows an untyped body to ChatAnswer, or returns null. Nothing downstream
 * casts: a body that does not match this shape is an error, not an answer.
 */
function parseAnswer(value: unknown): ChatAnswer | null {
  if (typeof value !== "object" || value === null) return null;
  const body = value as Record<string, unknown>;
  if (typeof body.answer !== "string") return null;
  if (typeof body.refused !== "boolean") return null;
  if (!Array.isArray(body.sources) || !body.sources.every(isSource)) {
    return null;
  }
  return {
    answer: body.answer,
    sources: body.sources,
    refused: body.refused,
  };
}

/** Tells the two 429s apart by DRF's own body, which is all the backend
    sends, always in English (it has no LocaleMiddleware). The per-visitor
    limit always knows its wait, so its `detail` reads "Request was
    throttled. Expected available in 42 seconds."; the daily cap has none to
    give (GlobalDailyThrottle.wait() is None) and stops at "Request was
    throttled." The body is only a hint: anything unreadable or without a
    `detail` is treated as the ordinary rate limit. */
async function isDailyCap(response: Response): Promise<boolean> {
  try {
    const body: unknown = await response.json();
    if (typeof body !== "object" || body === null) return false;
    const detail = (body as Record<string, unknown>).detail;
    return typeof detail === "string" && !detail.includes("Expected available");
  } catch {
    return false;
  }
}

export async function askChat(input: {
  question: string;
  history: ChatMessage[];
}): Promise<ChatResult> {
  if (!CHAT_API_URL) return { ok: false, error: "unconfigured" };

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    const response = await fetch(CHAT_API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: input.question,
        history: input.history.slice(-MAX_HISTORY),
      }),
      signal: controller.signal,
    });

    if (response.status === 429) {
      // Two limits answer 429. The per-visitor rate clears within a minute;
      // the site-wide daily cap holds until tomorrow, and a reader must not
      // be told "a minute" all day. DRF's `detail` is machine copy, so the
      // reader gets ours either way.
      return {
        ok: false,
        error: (await isDailyCap(response)) ? "dailyCap" : "throttled",
      };
    }
    if (!response.ok) return { ok: false, error: "server" };

    const parsed = parseAnswer(await response.json());
    return parsed
      ? { ok: true, data: parsed }
      : { ok: false, error: "malformed" };
  } catch {
    // A timeout, a CORS rejection, and an offline browser are the same event
    // to the reader: the question did not get through.
    return { ok: false, error: "network" };
  } finally {
    clearTimeout(timer);
  }
}
