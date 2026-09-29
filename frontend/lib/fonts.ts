import { Bricolage_Grotesque, Source_Serif_4, JetBrains_Mono } from "next/font/google";

const bricolage = Bricolage_Grotesque({
  variable: "--font-display",
  subsets: ["latin"],
  axes: ["wdth", "opsz"],
});

const sourceSerif = Source_Serif_4({
  variable: "--font-body",
  subsets: ["latin"],
  axes: ["opsz"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
});

/** The three families both languages use (Latin glyphs, and the English page). */
export const baseFontClass = `${bricolage.variable} ${sourceSerif.variable} ${jetbrainsMono.variable}`;
