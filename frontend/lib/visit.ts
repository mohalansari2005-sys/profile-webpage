import { CHAT_API_URL } from "@/lib/chat-api";

/**
 * Page views go to /api/visit/ on the backend the chat already talks to,
 * derived from the chat's URL so there is no second variable to configure.
 * Null when that URL is unset (nothing is sent) or not a URL at all.
 */
export const VISIT_URL = visitUrl(CHAT_API_URL);

function visitUrl(chatUrl: string | undefined): string | null {
  if (!chatUrl) return null;
  try {
    return new URL("/api/visit/", chatUrl).toString();
  } catch {
    return null;
  }
}

const OPT_OUT_KEY = "analytics";

/**
 * The owner's switch: `?analytics=off` on any page stops this browser counting
 * itself, `?analytics=on` undoes it. True when this page view must not be sent.
 */
export function optedOut(search: string): boolean {
  const choice = new URLSearchParams(search).get("analytics");
  try {
    if (choice === "off") localStorage.setItem(OPT_OUT_KEY, "off");
    if (choice === "on") localStorage.removeItem(OPT_OUT_KEY);
    return localStorage.getItem(OPT_OUT_KEY) === "off";
  } catch {
    // Storage blocked: the URL still decides for this page view.
    return choice === "off";
  }
}

export type Visit = { path: string; referrer: string; source: string };

/** Fire and forget. Never throws and never logs: analytics must not be able
    to break or clutter the page. */
export function sendVisit(visit: Visit): void {
  if (!VISIT_URL) return;
  // A string body goes out as text/plain, which needs no CORS preflight; the
  // backend parses it as JSON itself.
  const body = JSON.stringify(visit);
  try {
    if (navigator.sendBeacon?.(VISIT_URL, body)) return;
  } catch {
    // Fall through to fetch.
  }
  try {
    fetch(VISIT_URL, { method: "POST", body, keepalive: true, mode: "no-cors" }).catch(
      () => {},
    );
  } catch {
    // Nothing left to try; a lost page view is acceptable.
  }
}
