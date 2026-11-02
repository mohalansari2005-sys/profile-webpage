"use client";

import { useEffect } from "react";
import { forgetSwitch, optedOut, sendVisit } from "@/lib/visit";

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
