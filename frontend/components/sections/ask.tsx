"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { Reveal } from "@/components/reveal";
import { useJoin } from "@/components/join-context";
import { experience, projects } from "@/lib/content";
import { askChat, MAX_HISTORY, type ChatMessage, type ChatSource } from "@/lib/chat-api";

/** Only these records have a row to scroll to. `about-bio` and the faq
    records can be cited but are not rendered anywhere on the page, so their
    chips stay inert rather than pointing at nothing. */
const ROW_IDS = new Set([...experience, ...projects].map((record) => record.id));

/** Three questions the corpus can actually answer, so the first turn teaches
    the edges: a role, a project, and an faq that has no row on the page. */
const SEEDS = [
  "What did he build at Majara?",
  "What is Keyraa?",
  "Is he available for work?",
];

type Turn = {
  id: number;
  question: string;
  answer: string;
  sources: ChatSource[];
  refused: boolean;
};

function scrollToRecord(recordId: string) {
  const row = document.getElementById(`record-${recordId}`);
  if (!row) return;
  // Focus first, scroll second. `preventScroll` stops the focus call from
  // doing its own jump, but issuing it *after* scrollIntoView cancels the
  // smooth scroll already in flight and leaves the reader where they were.
  row.focus({ preventScroll: true });
  // No `behavior` argument on purpose: the page's own `scroll-behavior` is
  // smooth in CSS and forced to `auto` under prefers-reduced-motion, so
  // inheriting it is what makes the reduced-motion case correct.
  row.scrollIntoView({ block: "center" });
}

function historyFrom(turns: Turn[]): ChatMessage[] {
  return turns
    .flatMap((turn): ChatMessage[] => [
      { role: "user", content: turn.question },
      { role: "assistant", content: turn.answer },
    ])
    .slice(-MAX_HISTORY);
}

export function Ask() {
  const [value, setValue] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [pending, setPending] = useState<string | null>(null);
  const [failed, setFailed] = useState<{ question: string; message: string } | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const nextId = useRef(1);
  // `pending` only disables the input after a re-render, and a seed chip
  // supplies its own question rather than reading the (now-cleared) field, so
  // the state guard alone can be beaten by two activations in one tick.
  const inFlight = useRef(false);
  const { setCited } = useJoin();

  async function ask(question: string) {
    const trimmed = question.trim();
    if (!trimmed || inFlight.current) return;

    inFlight.current = true;
    setValue("");
    setFailed(null);
    setPending(trimmed);

    const result = await askChat({ question: trimmed, history: historyFrom(turns) });

    inFlight.current = false;
    setPending(null);
    if (!result.ok) {
      setFailed({ question: trimmed, message: result.message });
      return;
    }
    const id = nextId.current++;
    setTurns((current) => [...current, { id, question: trimmed, ...result.data }]);
    // A refusal cites nothing, so this clears the join rather than leaving a
    // pinned tool lit beside an answer that has nothing to do with it.
    setCited(result.data.sources.map((source) => source.record_id));
  }

  // Focus returns to the input once an answer has rendered, so a follow-up
  // needs no reaching for the mouse. It has to wait for the re-render: calling
  // focus() beside setPending(null) targets an input React has not re-enabled
  // yet, and focusing a disabled element silently does nothing.
  useEffect(() => {
    if (turns.length) inputRef.current?.focus();
  }, [turns.length]);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void ask(value);
  }

  return (
    <section id="ask" className="border-b border-rule bg-surface-raised">
      <div className="mx-auto grid w-full max-w-5xl gap-8 px-6 py-20 sm:py-28 md:grid-cols-[7.5rem_1fr] md:gap-6">
        <Reveal>
          <h2 className="field-label md:pt-2.5">Ask</h2>
        </Reveal>

        <div className="max-w-2xl">
          <Reveal delay={80}>
            <form onSubmit={onSubmit}>
              <label htmlFor="ask-input" className="sr-only">
                Ask a question about Mohammed&rsquo;s work
              </label>
              <div className="flex items-center gap-3 border-b border-foreground pb-3">
                <input
                  id="ask-input"
                  ref={inputRef}
                  value={value}
                  onChange={(event) => setValue(event.target.value)}
                  disabled={pending !== null}
                  maxLength={1000}
                  autoComplete="off"
                  placeholder="Ask about his work&hellip;"
                  className="w-full bg-transparent text-lg outline-none placeholder:text-dim disabled:opacity-50 sm:text-xl"
                />
                <button
                  type="submit"
                  disabled={pending !== null || !value.trim()}
                  className="field-label shrink-0 cursor-pointer rounded-sm px-1 transition-colors hover:text-foreground disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Ask
                </button>
              </div>
            </form>
          </Reveal>

          <Reveal delay={160}>
            <p className="mt-4 text-sm leading-relaxed text-dim">
              Answers come only from what Mohammed has written about his own
              work. Anything outside that, it declines.
            </p>
          </Reveal>

          {turns.length === 0 && !pending && (
            <Reveal delay={240}>
              <div className="mt-6">
                <p className="field-label mb-2.5">Try</p>
                <ul className="flex flex-wrap gap-1.5">
                  {SEEDS.map((seed) => (
                    <li key={seed}>
                      <button
                        type="button"
                        onClick={() => void ask(seed)}
                        className="cursor-pointer rounded-sm border border-rule bg-foreground/[0.04] px-2.5 py-1.5 font-mono text-xs tracking-[0.04em] transition-colors duration-200 hover:border-foreground"
                      >
                        {seed}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            </Reveal>
          )}

          {/* One live region for the whole transcript: the answer is what a
              screen reader needs announced, and `aria-busy` says the question
              is in flight without a spinner having to carry that alone. */}
          <div
            aria-live="polite"
            aria-busy={pending !== null}
            className="mt-10 empty:mt-0"
          >
            {turns.map((turn, index) => (
              <article
                key={turn.id}
                className="grid gap-2 border-t border-rule py-6 sm:grid-cols-[7.5rem_1fr] sm:gap-6"
              >
                <p className="field-label sm:pt-1">
                  {`Q.${String(index + 1).padStart(2, "0")}`}
                </p>
                <div>
                  <h3 className="text-lg leading-snug font-semibold text-balance">
                    {turn.question}
                  </h3>
                  <p
                    className={`mt-3 leading-relaxed ${turn.refused ? "text-dim" : ""}`}
                  >
                    {turn.answer}
                  </p>

                  {turn.sources.length > 0 && (
                    <div className="mt-4">
                      <p className="field-label mb-2">Sources</p>
                      <ul className="flex flex-wrap gap-1.5">
                        {turn.sources.map((source) => {
                          const hasRow = ROW_IDS.has(source.record_id);
                          return (
                            <li key={source.record_id}>
                              {hasRow ? (
                                <button
                                  type="button"
                                  onClick={() => scrollToRecord(source.record_id)}
                                  className="cursor-pointer rounded-sm border border-match bg-match/20 px-2.5 py-1.5 font-mono text-xs tracking-[0.04em] transition-colors duration-200 hover:border-foreground"
                                >
                                  <span aria-hidden="true">&uarr; </span>
                                  {source.title}
                                </button>
                              ) : (
                                <span className="rounded-sm border border-rule px-2.5 py-1.5 font-mono text-xs tracking-[0.04em] text-dim">
                                  {source.title}
                                </span>
                              )}
                            </li>
                          );
                        })}
                      </ul>
                    </div>
                  )}
                </div>
              </article>
            ))}

            {pending && (
              <article className="grid gap-2 border-t border-rule py-6 sm:grid-cols-[7.5rem_1fr] sm:gap-6">
                <p className="field-label sm:pt-1">Thinking&hellip;</p>
                <h3 className="text-lg leading-snug font-semibold text-balance opacity-50">
                  {pending}
                </h3>
              </article>
            )}

            {failed && (
              <article className="grid gap-2 border-t border-rule py-6 sm:grid-cols-[7.5rem_1fr] sm:gap-6">
                <p className="field-label sm:pt-1">Failed</p>
                <div>
                  <h3 className="text-lg leading-snug font-semibold text-balance opacity-50">
                    {failed.question}
                  </h3>
                  <p className="mt-3 leading-relaxed text-dim">{failed.message}</p>
                  <button
                    type="button"
                    onClick={() => void ask(failed.question)}
                    className="mt-3 cursor-pointer rounded-sm font-mono text-xs tracking-[0.06em] underline underline-offset-4 transition-colors hover:text-match-ink"
                  >
                    Try again
                  </button>
                </div>
              </article>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
