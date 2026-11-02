"use client";

import { useEffect } from "react";
import { forgetSwitch, optedOut, REDIRECTING, sendVisit } from "@/lib/visit";

// Module scope, not a ref: dev-mode Strict Mode mounts every component twice
// and a ref would reset with it. A real page load starts a fresh module (the
// two languages are separate root layouts, so moving between them is a full
// navigation), so this still allows exactly one beacon per page load.
let sent = false;

/** Counts this page view on the backend (lib/visit.ts). Renders nothing. */
export function VisitBeacon() {
  useEffect(() => {
    if (sent) return;
    sent = true;
    try {
      // On its way to /ar, which counts this visit and carries the query
      // there, so the analytics switch is read on that page too.
      if (document.documentElement.hasAttribute(REDIRECTING)) return;
      const off = optedOut(location.search);
      forgetSwitch();
      if (off) return;
      const params = new URLSearchParams(location.search);
      sendVisit({
        path: location.pathname,
        referrer: document.referrer,
        source: params.get("utm_source") ?? params.get("ref") ?? "",
      });
    } catch {
      // Analytics must never break the page.
    }
  }, []);
  return null;
}
