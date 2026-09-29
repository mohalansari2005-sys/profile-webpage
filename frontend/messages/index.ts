import type { Locale } from "@/lib/i18n";
import { ar } from "./ar";
import { en, type Messages } from "./en";

export type { Messages };

export function getMessages(locale: Locale): Messages {
  return locale === "ar" ? ar : en;
}
