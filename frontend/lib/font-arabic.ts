import { IBM_Plex_Sans_Arabic } from "next/font/google";

// Imported only by the /ar layout, so the English page never preloads it. It
// is not a variable font, hence the explicit weights (regular body, semibold
// and bold headings). The latin subset keeps Latin names inside Arabic text in
// the same family instead of falling back to another face.
const plexArabic = IBM_Plex_Sans_Arabic({
  variable: "--font-arabic",
  subsets: ["arabic", "latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

export const arabicFontClass = plexArabic.variable;
