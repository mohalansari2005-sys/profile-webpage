"use client";

import { useCallback, useState, type CSSProperties, type ReactNode } from "react";
import { cn } from "@/lib/utils";

type RevealProps = {
  children: ReactNode;
  /** Stagger offset in ms, for revealing a group in sequence. */
  delay?: number;
  className?: string;
};

/**
 * Reveals its children once, when they first scroll into view.
 *
 * Uses a ref callback rather than an effect so the observer attaches exactly
 * when the node does. Where IntersectionObserver is unavailable the content
 * shows immediately, and a <noscript> rule in the layout covers the
 * JS-disabled case — nothing is ever left hidden. Motion itself is disabled
 * in CSS under prefers-reduced-motion.
 */
export function Reveal({ children, delay = 0, className }: RevealProps) {
  const [revealed, setRevealed] = useState(false);

  const observe = useCallback((element: HTMLDivElement | null) => {
    if (!element) return;

    if (typeof IntersectionObserver === "undefined") {
      setRevealed(true);
      return;
    }

    // Anything already at or above the fold when it mounts has effectively
    // been seen — a deep link to #work, a restored scroll position, a reload
    // partway down. Show it outright rather than fading in content the reader
    // has already scrolled to. Plain geometry, so it holds even where observer
    // callbacks are suspended (a page opened in a background tab).
    if (element.getBoundingClientRect().top < window.innerHeight * 0.9) {
      setRevealed(true);
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setRevealed(true);
          observer.disconnect();
        }
      },
      {
        // The huge top margin is what makes this reliable. IntersectionObserver
        // only reports a *crossing*, so an element jumped clean over — an
        // anchor click, a restored scroll position, or any instant jump, which
        // is what prefers-reduced-motion users always get — goes from below the
        // viewport to above it without ever intersecting, and no callback
        // fires at all. Extending the root upward means "above the viewport"
        // still counts as intersecting, so passing an element is enough to
        // reveal it and nothing can be stranded at opacity 0.
        rootMargin: "100000px 0px -10% 0px",
        threshold: 0.08,
      },
    );

    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={observe}
      className={cn("reveal", className)}
      data-revealed={revealed}
      style={{ "--stagger": `${delay}ms` } as CSSProperties}
    >
      {children}
    </div>
  );
}
