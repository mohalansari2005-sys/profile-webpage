import { ImageResponse } from "next/og";
import { loadGoogleFont } from "@/lib/google-font";

export const alt = "Mohammed Alansari";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const dynamic = "force-static";

const PAPER = "#ebeef3";
const INK = "#0f1626";
const RULE = "#d2d8e0";
const MATCH_INK = "#8e5f15";

export default async function Image() {
  const displayText = "MAMohammedAlansari";
  const monoText = "PRODUCT ENGINEER AT MAJARA";

  const [displayBold, mono] = await Promise.all([
    loadGoogleFont("Bricolage+Grotesque", 800, displayText),
    loadGoogleFont("JetBrains+Mono", 500, monoText),
  ]);

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          padding: "80px 96px",
          backgroundColor: PAPER,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 40 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: 176,
              height: 176,
              borderRadius: 10,
              backgroundColor: INK,
              flexShrink: 0,
            }}
          >
            <span
              style={{
                fontFamily: "Bricolage Grotesque",
                fontWeight: 800,
                fontSize: 76,
                letterSpacing: "-0.03em",
                color: PAPER,
              }}
            >
              MA
            </span>
          </div>

          <div
            style={{
              display: "flex",
              flexDirection: "column",
              fontFamily: "Bricolage Grotesque",
              fontWeight: 800,
              fontSize: 88,
              lineHeight: 0.98,
              letterSpacing: "-0.03em",
              color: INK,
            }}
          >
            <span>Mohammed</span>
            <span>Alansari</span>
          </div>
        </div>

        <div style={{ display: "flex", width: 560, height: 1, marginTop: 56, backgroundColor: RULE }} />

        <div
          style={{
            display: "flex",
            marginTop: 32,
            fontFamily: "JetBrains Mono",
            fontWeight: 500,
            fontSize: 22,
            letterSpacing: "0.14em",
            color: MATCH_INK,
          }}
        >
          {monoText}
        </div>
      </div>
    ),
    {
      ...size,
      fonts: [
        { name: "Bricolage Grotesque", data: displayBold, weight: 800, style: "normal" },
        { name: "JetBrains Mono", data: mono, weight: 500, style: "normal" },
      ],
    },
  );
}
