"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { GithubIcon } from "@/components/github-icon";
import { useI18n } from "@/components/i18n-provider";
import { format, localize } from "@/lib/i18n";
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
  const { locale } = useI18n();
  const text = localize(record, locale);
  return (
    <Reveal delay={delay}>
      {/* scroll-mt-28 (112px) clears the sticky tool strip (91px, 99px on
          touch screens) when a source chip scrolls a record to the top. */}
      <article
        id={`record-${record.id}`}
        tabIndex={-1}
        data-state={state}
        className="group relative scroll-mt-28 border-b border-rule transition-opacity duration-200 data-[state=dim]:opacity-40 data-[state=dim]:hover:opacity-100 data-[state=dim]:focus-within:opacity-100"
      >
        {/* The match marker — the only place amber appears. */}
        <span
          aria-hidden="true"
          className="absolute top-0 bottom-0 -start-4 w-0.5 origin-top scale-y-0 bg-match opacity-0 transition duration-200 group-data-[state=lit]:scale-y-100 group-data-[state=lit]:opacity-100 sm:-start-6"
        />

        <div className="grid grid-cols-1 gap-2 py-6 sm:grid-cols-[7.5rem_1fr] sm:gap-6 sm:py-7">
          {/* The period is the record's key, in the same label column the hero
              fields and the contact links use. */}
          <p className="field-label sm:pt-2">{text.period}</p>

          <div>
            <h3
              className="font-display text-xl font-semibold tracking-tight sm:text-2xl"
              style={{ fontStretch: "90%" }}
            >
              {text.title}
            </h3>
            <p className="mt-1.5 font-mono text-xs tracking-[0.06em] text-dim">
              {text.org}
            </p>
            <p className="mt-3 max-w-xl leading-relaxed text-balance">
              {text.summary}
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

/** Chevron for the rail's paging buttons (Lucide's "chevron-right" path, ISC).
    Drawn inline rather than importing an icon package for two arrows; it
    flips itself in RTL, so the button that pages forward always points forward. */
function Chevron({ direction }: { direction: "left" | "right" }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={cn("size-4 rtl:rotate-180", direction === "left" && "scale-x-[-1]")}
    >
      <path d="m9 18 6-6-6-6" />
    </svg>
  );
}

/** One project as a rounded card in the horizontal rail. State styling mirrors
    RecordRow (lit on a tool/citation match, dim otherwise); the card border
    stands in for RecordRow's start-edge marker, which would be clipped by the
    rail's overflow. */
function ProjectCard({
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
  const { locale, t } = useI18n();
  const text = localize(record, locale);
  return (
    <Reveal delay={delay} className="w-[min(22rem,85vw)] shrink-0 snap-start">
      {/* scroll-mt-28: see RecordRow. */}
      <article
        id={`record-${record.id}`}
        tabIndex={-1}
        data-state={state}
        className="flex h-full scroll-mt-28 flex-col rounded-2xl border border-rule bg-foreground/[0.04] p-5 transition duration-200 data-[state=dim]:opacity-40 data-[state=dim]:hover:opacity-100 data-[state=dim]:focus-within:opacity-100 data-[state=lit]:border-match data-[state=lit]:bg-match/10"
      >
        <div className="flex items-start justify-between gap-3">
          <p className="field-label pt-1">{text.period}</p>
          {record.repo && (
            <a
              href={record.repo}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={format(t.work.onGithub, { title: text.title })}
              title={t.work.viewOnGithub}
              className="flex size-9 shrink-0 items-center justify-center rounded-full border border-rule transition-colors hover:border-foreground pointer-coarse:size-11"
            >
              <GithubIcon className="size-4" />
            </a>
          )}
        </div>

        <h3
          className="mt-3 font-display text-xl font-semibold tracking-tight sm:text-2xl"
          style={{ fontStretch: "90%" }}
        >
          {text.title}
        </h3>
        <p className="mt-1.5 font-mono text-xs tracking-[0.06em] text-dim">
          {text.org}
        </p>
        <p className="mt-3 leading-relaxed">{text.summary}</p>

        <ul className="mt-auto flex flex-wrap gap-1.5 pt-4">
          {record.tools.map((toolId) => {
            const tool = toolById.get(toolId);
            if (!tool) return null;
            const isMatch = activeTool === toolId;
            return (
              <li
                key={toolId}
                className={cn(
                  "rounded-full border px-2.5 py-1 font-mono text-[0.6875rem] tracking-[0.06em] transition-colors duration-200",
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
      </article>
    </Reveal>
  );
}

/** Projects side by side, scrolling sideways, so a growing list stays one
    row tall instead of a long stack. Chevrons page by one card. Direction-
    aware: scrollLeft is negative in RTL, and "previous" points the other way. */
function ProjectRail({
  rowState,
  activeTool,
}: {
  rowState: (record: WorkRecord) => RowState;
  activeTool: string | null;
}) {
  const { t } = useI18n();
  const railRef = useRef<HTMLDivElement>(null);
  const [canPrev, setCanPrev] = useState(false);
  const [canNext, setCanNext] = useState(false);
  const [overflows, setOverflows] = useState(false);

  const sync = useCallback(() => {
    const el = railRef.current;
    if (!el) return;
    const position = Math.abs(el.scrollLeft);
    const max = el.scrollWidth - el.clientWidth;
    setCanPrev(position > 1);
    setCanNext(position < max - 1);
    setOverflows(max > 1);
  }, []);

  useEffect(() => {
    sync();
    window.addEventListener("resize", sync);
    return () => window.removeEventListener("resize", sync);
  }, [sync]);

  function page(direction: "prev" | "next") {
    const el = railRef.current;
    if (!el) return;
    const rtl = getComputedStyle(el).direction === "rtl";
    const card = el.firstElementChild as HTMLElement | null;
    const step = (card?.offsetWidth ?? el.clientWidth) + 16; // card + gap-4
    const sign = (direction === "next" ? 1 : -1) * (rtl ? -1 : 1);
    el.scrollBy({ left: sign * step });
  }

  // aria-disabled, not `disabled`: paging to the end disables the chevron the
  // reader just pressed, and a natively disabled button drops keyboard focus
  // to <body>. This one keeps it and ignores the press. When every card fits,
  // though, neither chevron can ever page, so both are natively disabled and
  // Tab skips them.
  const chevron =
    "flex size-9 items-center justify-center rounded-full border border-rule bg-foreground/[0.04] transition-colors hover:border-foreground aria-disabled:cursor-not-allowed aria-disabled:opacity-40 aria-disabled:hover:border-rule pointer-coarse:size-11";

  return (
    <>
      <div className="mb-4 flex items-center justify-between">
        <Reveal>
          <h2 className="field-label">{t.work.projects}</h2>
        </Reveal>
        <div className="flex gap-2">
          <button
            type="button"
            aria-label={t.work.previousProject}
            aria-disabled={!canPrev}
            disabled={!overflows}
            onClick={() => canPrev && page("prev")}
            className={chevron}
          >
            <Chevron direction="left" />
          </button>
          <button
            type="button"
            aria-label={t.work.nextProject}
            aria-disabled={!canNext}
            disabled={!overflows}
            onClick={() => canNext && page("next")}
            className={chevron}
          >
            <Chevron direction="right" />
          </button>
        </div>
      </div>

      <div
        ref={railRef}
        data-project-rail=""
        onScroll={sync}
        className="gutter-bleed flex snap-x snap-mandatory gap-4 overflow-x-auto pb-2 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        {projects.map((record, index) => (
          <ProjectCard
            key={record.id}
            record={record}
            state={rowState(record)}
            activeTool={activeTool}
            delay={index * 70}
          />
        ))}
      </div>
    </>
  );
}

export function Work() {
  const { t } = useI18n();
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
    // scrollLeft is 0 at the start and grows negative going toward the end in
    // RTL, so measure distance travelled, not its sign.
    const travelled = Math.abs(el.scrollLeft);
    const atStart = travelled <= 1;
    const atEnd = travelled >= el.scrollWidth - el.clientWidth - 1;
    setEdge(
      atStart && atEnd ? "none" : atStart ? "end" : atEnd ? "start" : "both",
    );
  }, []);

  useEffect(() => {
    syncEdges();
    window.addEventListener("resize", syncEdges);
    return () => window.removeEventListener("resize", syncEdges);
  }, [syncEdges]);

  // Clear unmounts itself, which would drop keyboard focus to <body>. Hand it
  // to the strip's heading: focusing a chip instead would preview that tool
  // and light its rows straight back up, and from the heading the next Tab
  // reaches the first tool.
  const headingRef = useRef<HTMLHeadingElement>(null);
  function clearJoin() {
    clear();
    headingRef.current?.focus({ preventScroll: true });
  }

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
        <div className="mx-auto w-full max-w-5xl gutter py-3.5">
          <div className="flex items-baseline justify-between gap-4">
            <h2
              ref={headingRef}
              tabIndex={-1}
              className="field-label shrink-0 whitespace-nowrap"
            >
              {t.work.builtWith}
            </h2>
            <div className="flex min-w-0 items-baseline gap-3">
              <p
                aria-live="polite"
                className="min-w-0 truncate font-mono text-xs tracking-[0.1em] text-dim"
              >
                {activeLabel
                  ? format(t.work.toolMatch, {
                      count: matchCount,
                      total: experience.length + projects.length,
                      tool: activeLabel,
                    })
                  : litByCitation
                    ? format(t.work.cited, {
                        count: litByCitation.size,
                        total: experience.length + projects.length,
                      })
                    : t.work.pickTool}
              </p>
              {/* Beside the status it resets, not at the end of the strip,
                  which runs 1,400px or more past the column: there it was
                  always scrolled out of sight. The negative margins give it
                  a finger-sized target without making the bar taller. */}
              {(pinnedTool || citedRecordIds.length > 0) && (
                <button
                  type="button"
                  onClick={clearJoin}
                  className="-mx-1.5 -my-1.5 shrink-0 cursor-pointer rounded-sm px-1.5 py-1.5 font-mono text-xs tracking-[0.04em] whitespace-nowrap text-foreground underline underline-offset-4 transition-colors hover:text-match-ink pointer-coarse:-my-2.5 pointer-coarse:py-2.5"
                >
                  {t.work.clear}
                </button>
              )}
            </div>
          </div>

          <div
            ref={stripRef}
            onScroll={syncEdges}
            data-edge={edge}
            className="tool-strip gutter-bleed mt-2.5 overflow-x-auto pb-1"
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
                          onFocus={(event) => {
                            setHoveredTool(tool.id);
                            // The browser only scrolls a focused chip that is
                            // wholly out of view, so one half under the edge
                            // fade stayed there. Bring it fully in, but only
                            // for the keyboard: a mouse press or a tap focuses
                            // the chip too, and sliding it away before the
                            // release made the press miss it.
                            if (event.currentTarget.matches(":focus-visible")) {
                              event.currentTarget.scrollIntoView({
                                block: "nearest",
                                inline: "nearest",
                              });
                            }
                          }}
                          onBlur={() => setHoveredTool(null)}
                          onClick={() => toggleTool(tool.id)}
                          className={cn(
                            "shrink-0 cursor-pointer rounded-sm border px-2.5 py-1.5 font-mono text-xs tracking-[0.04em] whitespace-nowrap transition-colors duration-200 pointer-coarse:py-2.5",
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
            </ul>
          </div>
        </div>
      </div>

      <section className="border-b border-rule">
        <div className="mx-auto w-full max-w-5xl gutter py-16 sm:py-20">
          <Reveal>
            <h2 className="field-label mb-2">{t.work.experience}</h2>
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
        <div className="mx-auto w-full max-w-5xl gutter py-16 sm:py-20">
          <ProjectRail rowState={rowState} activeTool={activeTool} />
        </div>
      </section>
    </div>
  );
}
