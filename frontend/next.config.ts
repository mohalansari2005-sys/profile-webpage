import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  turbopack: { root: __dirname },
  experimental: {
    // The Arabic font's @font-face rules (~7 KB, lib/font-arabic.ts) are
    // imported by the /ar layout alone. The default chunking prices a request
    // at ~20 KB of CSS, so it merged them into the stylesheet `/` loads too,
    // and Next then preloaded all eight Plex files (~197 KB) on the English
    // page, which never draws them: the chunker weighs CSS bytes, not the
    // fonts they pull in. At ~1 KB a request, a stylesheet only one language
    // imports gets a chunk of its own; what both import still ships as one.
    cssChunking: { type: "graph", requestCost: 1000 },
  },
};

export default nextConfig;
