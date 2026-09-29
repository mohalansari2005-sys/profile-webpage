"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { ArrowUp, Bot } from "lucide-react";
import { useStickToBottomContext } from "use-stick-to-bottom";
import {
  Conversation,
  ConversationContent,
  ConversationScrollButton,
} from "@/components/ai-elements/conversation";
import { Message, MessageContent } from "@/components/ai-elements/message";
import { Suggestion, Suggestions } from "@/components/ai-elements/suggestion";
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

/** The message's side follows the page's direction; only the text inside
    follows the message's own (`dir="auto"`). Putting `dir` on the bubble
    itself would flip its `ms-auto` margin, sending an Arabic question to the
    wrong side of an English page. */
function UserMessage({ children, dim }: { children: string; dim?: boolean }) {
  return (
    <Message from="user" className={dim ? "opacity-70" : ""}>
      <MessageContent className="text-base leading-snug group-[.is-user]:rounded-2xl group-[.is-user]:rounded-ee-md">
        <p dir="auto">{children}</p>
      </MessageContent>
    </Message>
  );
}

function AssistantMessage({ children }: { children: React.ReactNode }) {
  return (
    <Message from="assistant">
      <MessageContent className="text-base leading-relaxed">{children}</MessageContent>
    </Message>
  );
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
          <p className="field-label md:pt-2.5">AI chat</p>
        </Reveal>

        <div className="max-w-2xl">
          <Reveal delay={80}>
            <h2
              className="font-display text-2xl leading-[1.15] font-semibold tracking-tight text-balance sm:text-4xl"
              style={{ fontStretch: "88%" }}
            >
              Ask my AI assistant about my work.
            </h2>
            <p className="mt-3 max-w-prose leading-relaxed text-dim">
              A chatbot that answers from what I&rsquo;ve written about my
              roles, projects and tools. Type a question, or tap a suggestion.
            </p>
          </Reveal>

          <Reveal delay={160}>
            <div className="mt-8 flex h-[min(36rem,72svh)] flex-col overflow-hidden rounded-3xl border border-rule bg-card shadow-sm">
              <div className="flex items-center gap-3 border-b border-rule px-5 py-3.5">
                <span
                  aria-hidden="true"
                  className="flex size-9 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground"
                >
                  <Bot className="size-5" />
                </span>
                <div className="leading-tight">
                  <p className="font-semibold">Mohammed&rsquo;s AI assistant</p>
                  <p className="mt-0.5 text-sm text-dim">
                    AI chatbot &middot; answers only from his portfolio
                  </p>
                </div>
              </div>

              <Conversation className="min-h-0 flex-1" aria-busy={pending !== null}>
                <ConversationContent className="gap-5 p-5">
                  <AssistantMessage>
                    <p>
                      Hi, I&rsquo;m an AI chatbot trained on Mohammed&rsquo;s
                      portfolio. Ask me about his work.
                    </p>
                    {turns.length === 0 && !pending && !failed && (
                      <Suggestions className="mt-1">
                        {SEEDS.map((seed) => (
                          <Suggestion
                            key={seed}
                            suggestion={seed}
                            onClick={(question) => void ask(question)}
                          />
                        ))}
                      </Suggestions>
                    )}
                  </AssistantMessage>

                  {turns.map((turn) => (
                    <div key={turn.id} id={`turn-${turn.id}`} className="flex flex-col gap-3">
                      <UserMessage>{turn.question}</UserMessage>
                      <AssistantMessage>
                        <p dir="auto" className={turn.refused ? "text-dim" : ""}>
                          {turn.answer}
                        </p>

                        {turn.sources.length > 0 && (
                          <div className="mt-4">
                            <p className="field-label mb-2">Sources</p>
                            <ul className="flex flex-wrap gap-2">
                              {turn.sources.map((source) => {
                                const hasRow = ROW_IDS.has(source.record_id);
                                return (
                                  <li key={source.record_id}>
                                    {hasRow ? (
                                      <button
                                        type="button"
                                        onClick={() => scrollToRecord(source.record_id)}
                                        className="cursor-pointer rounded-full border border-match bg-match/20 px-3 py-1.5 font-mono text-xs tracking-[0.04em] transition-colors duration-200 hover:border-foreground"
                                      >
                                        <span aria-hidden="true">&uarr; </span>
                                        {source.title}
                                      </button>
                                    ) : (
                                      <span className="rounded-full border border-rule px-3 py-1.5 font-mono text-xs tracking-[0.04em] text-dim">
                                        {source.title}
                                      </span>
                                    )}
                                  </li>
                                );
                              })}
                            </ul>
                          </div>
                        )}
                      </AssistantMessage>
                    </div>
                  ))}

                  {pending && (
                    <div className="flex flex-col gap-3">
                      <UserMessage dim>{pending}</UserMessage>
                      <AssistantMessage>
                        <p className="field-label">Thinking&hellip;</p>
                      </AssistantMessage>
                    </div>
                  )}

                  {failed && (
                    <div className="flex flex-col gap-3">
                      <UserMessage dim>{failed.question}</UserMessage>
                      <AssistantMessage>
                        <p className="text-dim">{failed.message}</p>
                        <button
                          type="button"
                          onClick={() => void ask(failed.question)}
                          className="mt-3 cursor-pointer rounded-full font-mono text-xs tracking-[0.06em] underline underline-offset-4 transition-colors hover:text-match-ink"
                        >
                          Try again
                        </button>
                      </AssistantMessage>
                    </div>
                  )}
                </ConversationContent>
                <KeepTurnInView
                  turnId={turns[turns.length - 1]?.id}
                  pending={pending !== null}
                />
                <ConversationScrollButton />
              </Conversation>

              <form onSubmit={onSubmit} className="border-t border-rule p-3.5">
                <label htmlFor="ask-input" className="sr-only">
                  Ask a question about Mohammed&rsquo;s work
                </label>
                <div className="flex items-center gap-2 rounded-full border border-rule bg-background py-1.5 ps-5 pe-1.5 transition-colors focus-within:border-foreground">
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
                    className="w-full bg-transparent py-1.5 text-base outline-none placeholder:text-dim disabled:opacity-50 sm:text-lg"
                  />
                  <button
                    type="submit"
                    aria-label="Send question"
                    disabled={pending !== null || !value.trim()}
                    className="flex size-10 shrink-0 cursor-pointer items-center justify-center rounded-full bg-primary text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    <ArrowUp className="size-5" aria-hidden="true" />
                  </button>
                </div>
              </form>
            </div>
          </Reveal>

          <Reveal delay={240}>
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
