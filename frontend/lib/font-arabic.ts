import { IBM_Plex_Sans_Arabic } from "next/font/google";

// Only the /ar layout applies it. It is not a variable font, hence the explicit
// weights (regular body, semibold and bold headings). The latin subset keeps
// Latin names inside Arabic text in the same family instead of falling back to
// another face.
//
// Not preloaded: Turbopack puts every @font-face in one CSS chunk shared by
// both layouts, and Next then preloads every font in it on both pages, so `/`
// fetched all eight Plex files (~197 KB) for text it never shows. Without the
// preload, /ar fetches the files once its CSS asks for them, and `swap` shows
// the size-matched fallback until they arrive.
const plexArabic = IBM_Plex_Sans_Arabic({
  variable: "--font-arabic",
  subsets: ["arabic", "latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
  preload: false,
});

export const arabicFontClass = plexArabic.variable;
