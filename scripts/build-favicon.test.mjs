import { test } from "node:test";
import assert from "node:assert/strict";
import { icoFromPng } from "./build-favicon.mjs";

// Just enough of a PNG for the header: the signature, then IHDR's length,
// type, width and height.
function pngHeader(width, height) {
  const png = Buffer.alloc(33);
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]).copy(png, 0);
  png.writeUInt32BE(13, 8);
  png.write("IHDR", 12, "ascii");
  png.writeUInt32BE(width, 16);
  png.writeUInt32BE(height, 20);
  return png;
}

test("wraps the PNG unchanged after a one-entry icon directory", () => {
  const png = pngHeader(32, 32);
  const ico = icoFromPng(png);
  assert.deepEqual(
    [ico.readUInt16LE(0), ico.readUInt16LE(2), ico.readUInt16LE(4)],
    [0, 1, 1],
  );
  assert.equal(ico[6], 32);
  assert.equal(ico[7], 32);
  assert.equal(ico.readUInt16LE(10), 1);
  assert.equal(ico.readUInt16LE(12), 32);
  assert.equal(ico.readUInt32LE(14), png.length);
  assert.equal(ico.readUInt32LE(18), 22);
  assert.ok(ico.subarray(22).equals(png));
});

test("writes 256 as 0, as the format asks", () => {
  const ico = icoFromPng(pngHeader(256, 256));
  assert.equal(ico[6], 0);
  assert.equal(ico[7], 0);
});

test("refuses anything that is not a PNG, or too large for an entry", () => {
  assert.throws(() => icoFromPng(Buffer.from("<html>404</html>")), /not a PNG/);
  assert.throws(() => icoFromPng(pngHeader(512, 512)), /too large/);
});
