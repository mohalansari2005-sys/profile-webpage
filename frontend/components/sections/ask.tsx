"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { useStickToBottomContext } from "use-stick-to-bottom";
import {
  Conversation,
  ConversationContent,
  ConversationScrollButton,
} from "@/components/ai-elements/conversation";
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

/** When the newest turn fits the box, StickToBottom already lands on its end.
    A turn taller than the box would land past its start instead, so pin the
    top of it — the question and the first lines of the answer — in view. Only
    the box scrolls: scrollTo on the scroller, never scrollIntoView, which
    would also move the page.

    `stopScroll` (needed so the library doesn't drag the view back down) leaves
    it un-stuck, so every other case re-sticks explicitly: a question being
    sent, and a turn that fits. */
function KeepTurnInView({
  turnId,
  pending,
}: {
  turnId: number | undefined;
  pending: boolean;
}) {
  const { scrollRef, stopScroll, scrollToBottom } = useStickToBottomContext();

  useEffect(() => {
    if (pending) void scrollToBottom();
  }, [pending, scrollToBottom]);

  useEffect(() => {
    if (turnId === undefined) return;
    const scroller = scrollRef.current;
    const turn = document.getElementById(`turn-${turnId}`);
    if (!scroller || !turn) return;
    if (turn.offsetHeight <= scroller.clientHeight) {
      void scrollToBottom();
      return;
    }

    stopScroll();
    const top =
      turn.getBoundingClientRect().top -
      scroller.getBoundingClientRect().top +
      scroller.scrollTop;
    const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
    scroller.scrollTo({ top: top - 16, behavior: reduced ? "auto" : "smooth" });
  }, [turnId, scrollRef, stopScroll, scrollToBottom]);

  return null;
}

/** The bubble's side follows the page's direction; only the text inside
    follows the message's own (`dir="auto"`). Putting `dir` on the bubble
    itself would flip its `ms-auto` margin, sending an Arabic question to the
    wrong side of an English page. */
function QuestionBubble({ children, dim }: { children: string; dim?: boolean }) {
  return (
    <div
      className={`ms-auto max-w-[85%] rounded-md bg-secondary px-3.5 py-2.5 leading-snug ${dim ? "opacity-70" : ""}`}
    >
      <p dir="auto">{children}</p>
    </div>
  );
}

const ANSWER_BUBBLE =
  "me-auto max-w-[85%] rounded-md border border-rule bg-background px-3.5 py-2.5 text-start leading-relaxed";

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
            <div className="flex h-[min(34rem,70svh)] flex-col overflow-hidden rounded-md border border-rule bg-card">
              <Conversation className="min-h-0 flex-1" aria-busy={pending !== null}>
                <ConversationContent className="gap-5 p-4">
                  {turns.length === 0 && !pending && !failed && (
                    <div className="my-auto">
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
                  )}

                  {turns.map((turn) => (
                    <div key={turn.id} id={`turn-${turn.id}`} className="flex flex-col gap-3">
                      <QuestionBubble>{turn.question}</QuestionBubble>
                      <div className={ANSWER_BUBBLE}>
                        <p dir="auto" className={turn.refused ? "text-dim" : ""}>
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
                    </div>
                  ))}

                  {pending && (
                    <div className="flex flex-col gap-3">
                      <QuestionBubble dim>{pending}</QuestionBubble>
                      <p className={`${ANSWER_BUBBLE} field-label`}>Thinking&hellip;</p>
                    </div>
                  )}

                  {failed && (
                    <div className="flex flex-col gap-3">
                      <QuestionBubble dim>{failed.question}</QuestionBubble>
                      <div className={ANSWER_BUBBLE}>
                        <p className="text-dim">{failed.message}</p>
                        <button
                          type="button"
                          onClick={() => void ask(failed.question)}
                          className="mt-3 cursor-pointer rounded-sm font-mono text-xs tracking-[0.06em] underline underline-offset-4 transition-colors hover:text-match-ink"
                        >
                          Try again
                        </button>
                      </div>
                    </div>
                  )}
                </ConversationContent>
                <KeepTurnInView
                  turnId={turns[turns.length - 1]?.id}
                  pending={pending !== null}
                />
                <ConversationScrollButton />
              </Conversation>

              <form onSubmit={onSubmit} className="border-t border-rule px-4 py-3">
                <label htmlFor="ask-input" className="sr-only">
                  Ask a question about Mohammed&rsquo;s work
                </label>
                <div className="flex items-center gap-3">
                  <input
                    id="ask-input"
                    ref={inputRef}
                    value={value}
                    onChange={(event) => setValue(event.target.value)}
                    disabled={pending !== null}
                    maxLength={1000}
                    autoComplete="off"
                    dir="auto"
                    placeholder="Ask about his work&hellip;"
                    className="w-full bg-transparent text-lg outline-none placeholder:text-dim disabled:opacity-50"
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
            </div>
          </Reveal>

          <Reveal delay={160}>
            <p className="mt-4 text-sm leading-relaxed text-dim">
              Answers come only from what Mohammed has written about his own
              work. Anything outside that, it declines.
            </p>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
