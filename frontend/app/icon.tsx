import { monogramIcon } from "@/lib/monogram-icon";

export const size = { width: 32, height: 32 };
export const contentType = "image/png";
export const dynamic = "force-static";

/** The browser-tab icon, in place of create-next-app's default favicon. */
export default function Icon() {
  return monogramIcon(size.width, 2);
}
