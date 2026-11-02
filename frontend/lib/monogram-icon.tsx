import { ImageResponse } from "next/og";
import { loadGoogleFont } from "@/lib/google-font";

// The hero's "MA" badge as the site icon: an ink square with the letters in the
// page's background colour, in the display face. Hex values because
// ImageResponse cannot read CSS variables; they are --ink and --paper from
// globals.css, the pair the OG image's badge uses too.
const PAPER = "#ebeef3";
const INK = "#0f1626";

// Both icons draw the same two letters, so they share one download: the first
// to render starts it, the other awaits the same promise. Started on first
// use, not at import: Next also imports the icon routes just to read `size`
// for the pages' <link> tags, where a download nobody awaits is wasted, and
// a failed one an unhandled rejection.
let monogramFont: Promise<ArrayBuffer> | undefined;

/** Rendered at build time by app/icon.tsx and app/apple-icon.tsx. Heavier
    than the hero's semibold, as in the OG image: at 16px a lighter stroke
    thins to nothing. */
export async function monogramIcon(size: number, radius: number) {
  monogramFont ??= loadGoogleFont("Bricolage+Grotesque", 800, "MA");
  const font = await monogramFont;
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          borderRadius: radius,
          backgroundColor: INK,
        }}
      >
        <span
          style={{
            fontFamily: "Bricolage Grotesque",
            fontWeight: 800,
            fontSize: Math.round(size * 0.46),
            letterSpacing: "-0.03em",
            color: PAPER,
          }}
        >
          MA
        </span>
      </div>
    ),
    {
      width: size,
      height: size,
      fonts: [{ name: "Bricolage Grotesque", data: font, weight: 800, style: "normal" }],
    },
  );
}
