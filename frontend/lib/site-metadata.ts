import type { Metadata } from "next";
import type { Locale } from "@/lib/i18n";
import { homePath } from "@/lib/i18n";
import { getMessages } from "@/messages";

const OG_IMAGE = { url: "/opengraph-image", width: 1200, height: 630 };

/** Per-locale metadata. The OG image is referenced explicitly: with one root
    layout per language there is no shared layout for Next to attach the
    app-level opengraph-image to. */
export function siteMetadata(locale: Locale): Metadata {
  const { meta } = getMessages(locale);
  return {
    metadataBase: new URL("https://profile-webpage-liart.vercel.app"),
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
