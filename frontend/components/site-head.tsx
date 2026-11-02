import { REDIRECTING } from "@/lib/visit";

// Runs before first paint, so a reader who chose dark (or whose OS is dark)
// never sees a light flash. Mirrors apply() in components/theme-toggle.tsx.
const themeScript = `try{var t=localStorage.getItem("theme"),r=document.documentElement;r.classList.toggle("dark",t==="dark"||(t!=="light"&&matchMedia("(prefers-color-scheme: dark)").matches));r.classList.toggle("light",t==="light")}catch(e){}`;

// Remembering the reader's language. The toggle links to `?lang=en` on the way
// to English, and /ar records itself on load, so the choice is stored however
// the link was opened. Both English branches keep the rest of the query and
// the hash, so a campaign tag (`?utm_source=`) or the analytics switch
// (`?analytics=off`) still reaches the page-view beacon.
//  - English page: `?lang=en` stores English and only `lang` is taken out of
//    the URL; a reader who chose Arabic earlier is sent to /ar when they open
//    `/`, and the page is marked as leaving first (REDIRECTING) so its own
//    beacon stays silent and /ar counts the visit once.
//  - Arabic page: stores Arabic.
// First-time visitors are never redirected.
const englishPageScript = `try{var u=new URL(location.href);if(u.searchParams.get("lang")==="en"){localStorage.setItem("lang","en");u.searchParams.delete("lang");history.replaceState(null,"",u.pathname+u.search+u.hash)}else if(localStorage.getItem("lang")==="ar"&&location.pathname==="/"){document.documentElement.setAttribute("${REDIRECTING}","");location.replace("/ar"+location.search+location.hash)}}catch(e){}`;
const arabicPageScript = `try{localStorage.setItem("lang","ar")}catch(e){}`;

/** Contents of <head> shared by both languages' root layouts, so the two cannot
    drift apart. */
export function SiteHead({ locale }: { locale: "en" | "ar" }) {
  return (
    <>
      <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      <script
        dangerouslySetInnerHTML={{
          __html: locale === "ar" ? arabicPageScript : englishPageScript,
        }}
      />
      {/* Without JS, scroll-revealed content would stay at opacity 0. */}
      <noscript>
        <style>{`.reveal,.field-in{opacity:1!important;transform:none!important}.rule-draw{transform:none!important}`}</style>
      </noscript>
    </>
  );
}
