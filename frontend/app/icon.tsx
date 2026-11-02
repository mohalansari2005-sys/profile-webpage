import { monogramIcon } from "@/lib/monogram-icon";

export const size = { width: 32, height: 32 };
export const contentType = "image/png";
export const dynamic = "force-static";

/** The browser-tab icon, in place of create-next-app's default favicon.

    app/favicon.ico is this same image in an .ico container, for whatever
    asks for /favicon.ico. It is committed, not built: after changing the
    image here or in lib/monogram-icon.tsx, build the frontend, then run
    `npm run favicon` from the repo root (scripts/build-favicon.mjs). */
export default function Icon() {
  return monogramIcon(size.width, 2);
}
