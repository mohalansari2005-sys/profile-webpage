// Runs before first paint, so a reader who chose dark (or whose OS is dark)
// never sees a light flash. Mirrors apply() in components/theme-toggle.tsx.
const themeScript = `try{var t=localStorage.getItem("theme"),r=document.documentElement;r.classList.toggle("dark",t==="dark"||(t!=="light"&&matchMedia("(prefers-color-scheme: dark)").matches));r.classList.toggle("light",t==="light")}catch(e){}`;

// English only: a reader who chose Arabic earlier is sent to /ar when they open
// `/`. Set by components/language-toggle.tsx; without it `/` stays English.
const rememberedLanguageScript = `try{if(localStorage.getItem("lang")==="ar"&&location.pathname==="/")location.replace("/ar"+location.hash)}catch(e){}`;

/** Contents of <head> shared by both languages' root layouts, so the two cannot
    drift apart. */
export function SiteHead({ restoreArabic = false }: { restoreArabic?: boolean }) {
  return (
    <>
      <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      {restoreArabic && (
        <script dangerouslySetInnerHTML={{ __html: rememberedLanguageScript }} />
      )}
      {/* Without JS, scroll-revealed content would stay at opacity 0. */}
      <noscript>
        <style>{`.reveal,.field-in{opacity:1!important;transform:none!important}.rule-draw{transform:none!important}`}</style>
      </noscript>
    </>
  );
}
