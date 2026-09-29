import type { Metadata } from "next";
import type { ReactNode } from "react";
import { SiteLayout } from "@/components/site-layout";
import { arabicFontClass } from "@/lib/font-arabic";
import { siteMetadata } from "@/lib/site-metadata";

export const metadata: Metadata = siteMetadata("ar");

export default function ArabicLayout({ children }: { children: ReactNode }) {
  return (
    <SiteLayout locale="ar" fontClass={arabicFontClass}>
      {children}
    </SiteLayout>
  );
}
