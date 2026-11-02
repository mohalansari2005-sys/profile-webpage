// Writes frontend/app/favicon.ico from the 32px monogram app/icon.tsx renders,
// for the browsers, feed readers and crawlers that ask for /favicon.ico
// whatever the page links. The pages link the PNG icons; this is the same
// image in the container that path is expected to hold.
//
// The icon is drawn at build time, so build first:
//   (cd frontend && npm run build) && npm run favicon
// Rerun it whenever app/icon.tsx or lib/monogram-icon.tsx changes the image.
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join, dirname } from "node:path";

const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
const HEADER_BYTES = 6 + 16; // ICONDIR, then one ICONDIRENTRY

/** An .ico holding one PNG image as it is, which every current browser and
    Windows since Vista read; no need to re-encode it as a bitmap. */
export function icoFromPng(png) {
  if (png.length < 24 || !png.subarray(0, 8).equals(PNG_SIGNATURE)) {
    throw new Error("not a PNG: expected the image frontend/out/icon holds");
  }
  // IHDR is always the first chunk: width and height follow its type.
  const width = png.readUInt32BE(16);
  const height = png.readUInt32BE(20);
  if (width > 256 || height > 256) {
    throw new Error(`${width}x${height} is too large for an .ico entry (256 at most)`);
  }
  const header = Buffer.alloc(HEADER_BYTES);
  header.writeUInt16LE(0, 0); // reserved
  header.writeUInt16LE(1, 2); // type: icon
  header.writeUInt16LE(1, 4); // one image
  header.writeUInt8(width % 256, 6); // 0 stands for 256
  header.writeUInt8(height % 256, 7);
  header.writeUInt8(0, 8); // no palette
  header.writeUInt8(0, 9); // reserved
  header.writeUInt16LE(1, 10); // colour planes
  header.writeUInt16LE(32, 12); // bits per pixel
  header.writeUInt32LE(png.length, 14);
  header.writeUInt32LE(HEADER_BYTES, 18); // the PNG starts right after
  return Buffer.concat([header, png]);
}

const here = dirname(fileURLToPath(import.meta.url));
const SOURCE = join(here, "..", "frontend", "out", "icon");
const TARGET = join(here, "..", "frontend", "app", "favicon.ico");

if (import.meta.main) {
  let png;
  try {
    png = readFileSync(SOURCE);
  } catch {
    console.error(`no ${SOURCE}: build the frontend first (cd frontend && npm run build)`);
    process.exit(1);
  }
  writeFileSync(TARGET, icoFromPng(png));
  console.log(`wrote ${TARGET}`);
}
