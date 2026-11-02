/** A Google Font's TrueType/OpenType data, subset to `text`, for the images
    rendered at build time (app/opengraph-image.tsx, app/icon.tsx,
    app/apple-icon.tsx). ImageResponse needs the font file itself: it cannot
    read the page's CSS or next/font.

    Both responses are checked: an error page read as CSS only surfaced as
    "could not resolve font data", and one read as a font failed inside
    ImageResponse with an error naming neither the font nor the request. */
export async function loadGoogleFont(family: string, weight: number, text: string) {
  const cssUrl = `https://fonts.googleapis.com/css2?family=${family}:wght@${weight}&text=${encodeURIComponent(text)}`;
  const cssResponse = await fetch(cssUrl);
  if (!cssResponse.ok) {
    throw new Error(
      `Google Fonts CSS for ${family} ${weight}: HTTP ${cssResponse.status} from ${cssUrl}`,
    );
  }
  const css = await cssResponse.text();
  const match = css.match(/src: url\(([^)]+)\) format\('(opentype|truetype)'\)/);
  if (!match) throw new Error(`could not resolve font data for ${family}`);
  const fontResponse = await fetch(match[1]);
  if (!fontResponse.ok) {
    throw new Error(
      `Google Fonts file for ${family} ${weight}: HTTP ${fontResponse.status} from ${match[1]}`,
    );
  }
  return fontResponse.arrayBuffer();
}
