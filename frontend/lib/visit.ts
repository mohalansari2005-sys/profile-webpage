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

/**
 * Set on <html> by site-head.tsx's script just before it sends a returning
 * Arabic reader from / on to /ar; /ar counts the visit. A guard: Chromium,
 * Firefox and WebKit all stop running / once the redirect starts (seen under
 * Playwright), but a browser that kept running it until /ar arrived would
 * send its beacon too and count the visit twice.
 */
export const REDIRECTING = "data-redirecting";

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

/**
 * Takes `analytics=` back out of the address bar once optedOut() has read it,
 * so a copied, bookmarked or autocompleted link cannot quietly opt out
 * everyone who opens it. Only that parameter goes; the others and the hash
 * stay, the same way site-head.tsx takes out `lang=en`.
 */
export function forgetSwitch(): void {
  try {
    const url = new URL(location.href);
    if (!url.searchParams.has(OPT_OUT_KEY)) return;
    url.searchParams.delete(OPT_OUT_KEY);
    history.replaceState(null, "", url.pathname + url.search + url.hash);
  } catch {
    // The parameter stays; this page view was still decided correctly.
  }
}

export type Visit = { path: string; referrer: string; source: string };

/** Fire and forget. Never throws and never logs from here: analytics must not
    be able to break or clutter the page. The browser itself still reports a
    beacon that fails (backend down, 429, an ad blocker) in the console. */
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
