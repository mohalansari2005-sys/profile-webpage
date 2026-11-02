import { monogramIcon } from "@/lib/monogram-icon";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";
export const dynamic = "force-static";

/** The home-screen icon on iOS. Square corners: iOS rounds them itself, and
    would fill transparent ones with black. */
export default function AppleIcon() {
  return monogramIcon(size.width, 0);
}
