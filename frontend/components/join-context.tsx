"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

/**
 * The one thing on the page that is "relevant right now", and where that
 * came from. Two sources, never both at once: a tool picked in the strip, or
 * the records an answer cited. Amber means the same thing either way, so a
 * single value has to own it — a tool highlight and a citation highlight
 * living side by side would make the dim state stop meaning one thing.
 */
export type Join =
  | { kind: "tool"; toolId: string }
  | { kind: "cited"; recordIds: string[] }
  | null;

type JoinContextValue = {
  /** The committed join: a pinned tool, a set of cited records, or nothing. */
  join: Join;
  /**
   * The tool driving the lit state at this instant. Hover and focus preview a
   * tool without committing it, and outrank whatever is committed — letting go
   * falls back to the pin, or to the citation underneath it.
   */
  activeTool: string | null;
  /** Records lit by a citation. Empty while a tool is previewed or pinned. */
  citedRecordIds: string[];
  /** The pinned tool, for `aria-pressed`. Null while only a citation is live. */
  pinnedTool: string | null;
  setHoveredTool: (toolId: string | null) => void;
  toggleTool: (toolId: string) => void;
  setCited: (recordIds: string[]) => void;
  clear: () => void;
};

const JoinContext = createContext<JoinContextValue | null>(null);

export function JoinProvider({ children }: { children: ReactNode }) {
  const [join, setJoin] = useState<Join>(null);
  const [hoveredTool, setHoveredTool] = useState<string | null>(null);

  const toggleTool = useCallback(
    (toolId: string) => {
      const isPinned = join?.kind === "tool" && join.toolId === toolId;
      setJoin(isPinned ? null : { kind: "tool", toolId });
      // The pointer is still on the tag after the click, so the hover preview
      // has to be released alongside the pin — otherwise it keeps holding the
      // tool and toggling off looks like nothing happened.
      setHoveredTool(isPinned ? null : toolId);
    },
    [join],
  );

  const setCited = useCallback((recordIds: string[]) => {
    // Asking is an action: it takes the join, pin and all. An answer that
    // cites nothing (a refusal) clears it rather than leaving a stale tool lit
    // next to an answer that has nothing to do with it.
    setJoin(recordIds.length ? { kind: "cited", recordIds } : null);
    setHoveredTool(null);
  }, []);

  const clear = useCallback(() => {
    setJoin(null);
    setHoveredTool(null);
  }, []);

  const value = useMemo<JoinContextValue>(() => {
    const pinnedTool = join?.kind === "tool" ? join.toolId : null;
    const activeTool = hoveredTool ?? pinnedTool;
    return {
      join,
      activeTool,
      // A previewed tool wins outright, so the two highlights never overlap.
      citedRecordIds:
        !activeTool && join?.kind === "cited" ? join.recordIds : [],
      pinnedTool,
      setHoveredTool,
      toggleTool,
      setCited,
      clear,
    };
  }, [join, hoveredTool, toggleTool, setCited, clear]);

  return <JoinContext.Provider value={value}>{children}</JoinContext.Provider>;
}

export function useJoin(): JoinContextValue {
  const value = useContext(JoinContext);
  if (!value) {
    throw new Error("useJoin must be used inside <JoinProvider>");
  }
  return value;
}
