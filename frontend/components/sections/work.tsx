"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Reveal } from "@/components/reveal";
import { useJoin } from "@/components/join-context";
import { cn } from "@/lib/utils";
import {
  experience,
  projects,
  toolById,
  toolGroups,
  tools,
  type WorkRecord,
} from "@/lib/content";

const groupOrder = toolGroups;

type RowState = "neutral" | "lit" | "dim";

function RecordRow({
  record,
  state,
  activeTool,
  delay,
}: {
  record: WorkRecord;
  state: RowState;
  activeTool: string | null;
  delay: number;
}) {
  return (
    <Reveal delay={delay}>
      <article
        id={`record-${record.id}`}
        tabIndex={-1}
        data-state={state}
        className="group relative border-b border-rule transition-opacity duration-200 data-[state=dim]:opacity-40 data-[state=dim]:hover:opacity-100 data-[state=dim]:focus-within:opacity-100"
      >
        {/* The match marker — the only place amber appears. */}
        <span
          aria-hidden="true"
          className="absolute top-0 bottom-0 -left-4 w-0.5 origin-top scale-y-0 bg-match opacity-0 transition duration-200 group-data-[state=lit]:scale-y-100 group-data-[state=lit]:opacity-100 sm:-left-6"
        />

        <div className="grid gap-2 py-6 sm:grid-cols-[7.5rem_1fr] sm:gap-6 sm:py-7">
          {/* The period is the record's key, in the same label column the hero
              fields and the contact links use. */}
          <p className="field-label sm:pt-2">{record.period}</p>

          <div>
            <h3
              className="font-display text-xl font-semibold tracking-tight sm:text-2xl"
              style={{ fontStretch: "90%" }}
            >
              {record.title}
            </h3>
            <p className="mt-1.5 font-mono text-xs tracking-[0.06em] text-dim">
              {record.org}
            </p>
            <p className="mt-3 max-w-xl leading-relaxed text-balance">
              {record.summary}
            </p>

            <ul className="mt-4 flex flex-wrap gap-1.5">
              {record.tools.map((toolId) => {
                const tool = toolById.get(toolId);
                if (!tool) return null;
                const isMatch = activeTool === toolId;
                return (
                  <li
                    key={toolId}
                    className={cn(
                      "rounded-sm border px-2 py-1 font-mono text-[0.6875rem] tracking-[0.06em] transition-colors duration-200",
                      isMatch
                        ? "border-match bg-match/20 text-foreground"
                        : "border-rule text-dim",
                    )}
                  >
                    {tool.label}
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      </article>
    </Reveal>
  );
}

export function Work() {
  const { activeTool, citedRecordIds, pinnedTool, setHoveredTool, toggleTool, clear } =
    useJoin();

  // The strip is wider than the column, so it scrolls sideways. Fade only the
  // edge that still has tags behind it — a clipped tag then reads as "more
  // this way" instead of "cut off", and nothing is dimmed once you reach it.
  const stripRef = useRef<HTMLDivElement>(null);
  const [edge, setEdge] = useState<"none" | "start" | "end" | "both">("none");

  const syncEdges = useCallback(() => {
    const el = stripRef.current;
    if (!el) return;
    const atStart = el.scrollLeft <= 1;
    const atEnd = el.scrollLeft >= el.scrollWidth - el.clientWidth - 1;
    setEdge(
      atStart && atEnd ? "none" : atStart ? "end" : atEnd ? "start" : "both",
    );
  }, []);

  // Re-measured on pin too: the Clear button changes the strip's width.
  useEffect(() => {
    syncEdges();
    window.addEventListener("resize", syncEdges);
    return () => window.removeEventListener("resize", syncEdges);
  }, [syncEdges, pinnedTool, citedRecordIds]);

  const matchCount = useMemo(() => {
    if (!activeTool) return 0;
    return [...experience, ...projects].filter((record) =>
      record.tools.includes(activeTool),
    ).length;
  }, [activeTool]);

  // Rows dim only when something is actually lit. A citation that names only
  // records with no row on the page — about-bio, an faq — must not dim the
  // whole list to highlight nothing.
  const litByCitation = useMemo(() => {
    if (!citedRecordIds.length) return null;
    const rows = new Set([...experience, ...projects].map((r) => r.id));
    const lit = citedRecordIds.filter((id) => rows.has(id));
    return lit.length ? new Set(lit) : null;
  }, [citedRecordIds]);

  function rowState(record: WorkRecord): RowState {
    if (activeTool) {
      return record.tools.includes(activeTool) ? "lit" : "dim";
    }
    if (litByCitation) {
      return litByCitation.has(record.id) ? "lit" : "dim";
    }
    return "neutral";
  }

  const activeLabel = activeTool ? toolById.get(activeTool)?.label : null;

  return (
    <div id="work">
      {/* Near-opaque on purpose: the row tool tags below are chips of the same
          shape as the strip's own, so at 85% they read through as a double
          render rather than as depth. */}
      <div className="sticky top-0 z-20 border-b border-rule bg-background/95 backdrop-blur-md">
        <div className="mx-auto w-full max-w-5xl px-6 py-3.5">
          <div className="flex items-baseline justify-between gap-4">
            <h2 className="field-label">Built with</h2>
            <p
              aria-live="polite"
              className="font-mono text-xs tracking-[0.1em] text-dim"
            >
              {activeLabel
                ? `${matchCount} of ${experience.length + projects.length} use ${activeLabel}`
                : litByCitation
                  ? `${litByCitation.size} of ${experience.length + projects.length} cited in the answer`
                  : "Pick a tool to see where it was used"}
            </p>
          </div>

          <div
            ref={stripRef}
            onScroll={syncEdges}
            data-edge={edge}
            className="tool-strip -mx-6 mt-2.5 overflow-x-auto px-6 pb-1"
          >
            <ul className="flex w-max items-center gap-1.5">
              {groupOrder.map((group, groupIndex) => (
                <li key={group} className="contents">
                  {groupIndex > 0 && (
                    <span
                      aria-hidden="true"
                      className="mx-1.5 h-4 w-px shrink-0 bg-rule"
                    />
                  )}
                  {tools
                    .filter((tool) => tool.group === group)
                    .map((tool) => {
                      const isActive = activeTool === tool.id;
                      const isPinned = pinnedTool === tool.id;
                      return (
                        <button
                          key={tool.id}
                          type="button"
                          aria-pressed={isPinned}
                          onMouseEnter={() => setHoveredTool(tool.id)}
                          onMouseLeave={() => setHoveredTool(null)}
                          onFocus={() => setHoveredTool(tool.id)}
                          onBlur={() => setHoveredTool(null)}
                          onClick={() => toggleTool(tool.id)}
                          className={cn(
                            "shrink-0 cursor-pointer rounded-sm border px-2.5 py-1.5 font-mono text-xs tracking-[0.04em] whitespace-nowrap transition-colors duration-200",
                            isActive
                              ? "border-match bg-match/20 text-foreground"
                              : activeTool
                                ? "border-rule bg-foreground/[0.04] text-dim"
                                : "border-rule bg-foreground/[0.04] text-foreground hover:border-foreground",
                          )}
                        >
                          {tool.label}
                        </button>
                      );
                    })}
                </li>
              ))}

              {(pinnedTool || citedRecordIds.length > 0) && (
                <li className="contents">
                  <span
                    aria-hidden="true"
                    className="mx-1.5 h-4 w-px shrink-0 bg-rule"
                  />
                  <button
                    type="button"
                    onClick={clear}
                    className="shrink-0 cursor-pointer rounded-sm px-2.5 py-1.5 font-mono text-xs tracking-[0.04em] whitespace-nowrap text-foreground underline underline-offset-4 transition-colors hover:text-match-ink"
                  >
                    Clear
                  </button>
                </li>
              )}
            </ul>
          </div>
        </div>
      </div>

      <section className="border-b border-rule">
        <div className="mx-auto w-full max-w-5xl px-6 py-16 sm:py-20">
          <Reveal>
            <h2 className="field-label mb-2">Experience</h2>
          </Reveal>
          {experience.map((record, index) => (
            <RecordRow
              key={record.id}
              record={record}
              state={rowState(record)}
              activeTool={activeTool}
              delay={index * 70}
            />
          ))}
        </div>
      </section>

      <section className="on-deep border-b border-rule bg-surface-deep">
        <div className="mx-auto w-full max-w-5xl px-6 py-16 sm:py-20">
          <Reveal>
            <h2 className="field-label mb-2">Projects</h2>
          </Reveal>
          {projects.map((record, index) => (
            <RecordRow
              key={record.id}
              record={record}
              state={rowState(record)}
              activeTool={activeTool}
              delay={index * 70}
            />
          ))}
        </div>
      </section>
    </div>
  );
}
