/**
 * The browser's whole view of the chat backend.
 *
 * The only environment variable the frontend gets is the API's URL, which is
 * safe to inline into the bundle. The Gemini key lives exclusively in the
 * Django container — that separation is the reason the backend exists, so
 * nothing in `frontend/` may ever read a GEMINI_* variable.
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
  | { ok: false; message: string };

/**
 * Everything the reader might see when a request does not produce an answer.
 * A refusal is *not* one of these — a refusal is a successful, grounded
 * "I can't answer that from the corpus" and arrives as `ok: true`.
 */
const MESSAGES = {
  throttled: "Too many questions right now — try again in a minute.",
  server: "The answer service hit an error. Try again in a moment.",
  network: "Couldn't reach the answer service.",
  malformed: "The answer service sent back something unexpected.",
  unconfigured: "The answer service isn't configured for this build.",
} as const;

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

export async function askChat(input: {
  question: string;
  history: ChatMessage[];
}): Promise<ChatResult> {
  if (!CHAT_API_URL) return { ok: false, message: MESSAGES.unconfigured };

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
      // DRF's own `detail` is machine copy ("Expected available in 42
      // seconds."), so the reader gets ours instead.
      return { ok: false, message: MESSAGES.throttled };
    }
    if (!response.ok) return { ok: false, message: MESSAGES.server };

    const parsed = parseAnswer(await response.json());
    return parsed
      ? { ok: true, data: parsed }
      : { ok: false, message: MESSAGES.malformed };
  } catch {
    // A timeout, a CORS rejection, and an offline browser are the same event
    // to the reader: the question did not get through.
    return { ok: false, message: MESSAGES.network };
  } finally {
    clearTimeout(timer);
  }
}
