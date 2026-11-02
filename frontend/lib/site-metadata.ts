import type { Metadata } from "next";
import type { Locale } from "@/lib/i18n";
import { homePath } from "@/lib/i18n";
import { getMessages } from "@/messages";

// The static export writes this PNG without an extension, so Vercel would
// serve it as application/octet-stream, which some link-preview crawlers
// reject; frontend/vercel.json sets its Content-Type, and `type` says so here.
const OG_IMAGE = { url: "/opengraph-image", width: 1200, height: 630, type: "image/png" };

/** Per-locale metadata. The OG image is referenced explicitly: with one root
    layout per language there is no shared layout for Next to attach the
    app-level opengraph-image to. */
export function siteMetadata(locale: Locale): Metadata {
  const { meta } = getMessages(locale);
  return {
    // The custom domain, not a *.vercel.app alias: canonical, hreflang and
    // og:url are all resolved against this, and search engines index whichever
    // host the canonical names.
    metadataBase: new URL("https://www.alansari.stream"),
    title: meta.title,
    description: meta.description,
    alternates: {
      canonical: homePath(locale),
      languages: { en: "/", ar: "/ar", "x-default": "/" },
    },
    openGraph: {
      title: meta.title,
      description: meta.description,
      type: "website",
      url: homePath(locale),
      locale: locale === "ar" ? "ar_SA" : "en_US",
      images: [{ ...OG_IMAGE, alt: meta.ogAlt }],
    },
    twitter: {
      card: "summary_large_image",
      title: meta.title,
      description: meta.description,
      images: [OG_IMAGE.url],
    },
  };
}
