/** A Google Font's TrueType/OpenType data, subset to `text`, for the images
    rendered at build time (app/opengraph-image.tsx, app/icon.tsx,
    app/apple-icon.tsx). ImageResponse needs the font file itself: it cannot
    read the page's CSS or next/font. */
export async function loadGoogleFont(family: string, weight: number, text: string) {
  const css = await (
    await fetch(
      `https://fonts.googleapis.com/css2?family=${family}:wght@${weight}&text=${encodeURIComponent(text)}`,
    )
  ).text();
  const match = css.match(/src: url\(([^)]+)\) format\('(opentype|truetype)'\)/);
  if (!match) throw new Error(`could not resolve font data for ${family}`);
  const res = await fetch(match[1]);
  return res.arrayBuffer();
}
