import type { Metadata } from "next";
import type { ReactNode } from "react";
import { SiteLayout } from "@/components/site-layout";
import { siteMetadata } from "@/lib/site-metadata";

export const metadata: Metadata = siteMetadata("en");

export default function EnglishLayout({ children }: { children: ReactNode }) {
  return <SiteLayout locale="en">{children}</SiteLayout>;
}
