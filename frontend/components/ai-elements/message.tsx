"use client";

// Trimmed from AI Elements' `message` (registry.ai-sdk.dev/message.json): only
// Message and MessageContent are kept. The rest (markdown via `streamdown`,
// attachments, branching, tooltip actions) added ~170 kB gzipped of JavaScript
// for features plain-text answers do not use. `ml-auto` is `ms-auto` so the
// user's side follows the page direction.

import { cn } from "@/lib/utils";
import type { HTMLAttributes } from "react";

export type MessageProps = HTMLAttributes<HTMLDivElement> & {
  from: "user" | "assistant" | "system";
};

export const Message = ({ className, from, ...props }: MessageProps) => (
  <div
    className={cn(
      "group flex w-full max-w-[95%] flex-col gap-2",
      from === "user" ? "is-user ms-auto justify-end" : "is-assistant",
      className
    )}
    {...props}
  />
);

export type MessageContentProps = HTMLAttributes<HTMLDivElement>;

export const MessageContent = ({
  children,
  className,
  ...props
}: MessageContentProps) => (
  <div
    className={cn(
      "flex w-fit max-w-full min-w-0 flex-col gap-2 overflow-hidden text-sm",
      "group-[.is-user]:ms-auto group-[.is-user]:rounded-lg group-[.is-user]:bg-secondary group-[.is-user]:px-4 group-[.is-user]:py-3 group-[.is-user]:text-foreground",
      "group-[.is-assistant]:text-foreground",
      className
    )}
    {...props}
  >
    {children}
  </div>
);
