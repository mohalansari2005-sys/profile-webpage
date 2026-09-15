import type { Metadata } from "next";
import { Bricolage_Grotesque, Source_Serif_4, JetBrains_Mono } from "next/font/google";
import "./globals.css";

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

const description =
  "Mohammed Alansari — Product Engineer at Majara and Computer Information Systems student at King Saud University, building backend systems, data pipelines, and AI-enabled applications.";

export const metadata: Metadata = {
  metadataBase: new URL("https://profile-webpage-liart.vercel.app"),
  title: "Mohammed Alansari",
  description,
  openGraph: {
    title: "Mohammed Alansari",
    description,
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Mohammed Alansari",
    description,
  },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${bricolage.variable} ${sourceSerif.variable} ${jetbrainsMono.variable} h-full antialiased`}
    >
      <head>
        {/* Without JS, scroll-revealed content would stay at opacity 0. */}
        <noscript>
          <style>{`.reveal,.field-in{opacity:1!important;transform:none!important}.rule-draw{transform:none!important}`}</style>
        </noscript>
      </head>
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
