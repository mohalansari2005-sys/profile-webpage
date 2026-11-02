import { expect, test } from "./fixtures";

// The chat API URL is baked in at build time (see CI), and every request to it
// is intercepted here, so these tests never touch a real backend or OpenAI.
const CHAT_API = "http://chat.test/api/chat/";

test("renders every section", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("h1")).toBeVisible();
  for (const name of ["About", "Experience", "Projects", "Ask my AI assistant about my work.", "Contact"]) {
    await expect(
      page.getByRole("heading", { level: 2, name, exact: true }),
    ).toBeVisible();
  }
});

test("chat round-trip shows the mocked answer", async ({ page }) => {
  await page.route(CHAT_API, (route) =>
    route.fulfill({
      json: {
        answer: "Mocked answer about Mohammed.",
        sources: [],
        refused: false,
      },
    }),
  );
  await page.goto("/");
  await page.locator("#ask-input").fill("What does he do?");
  await page.getByRole("button", { name: "Send question" }).click();
  await expect(page.getByText("Mocked answer about Mohammed.")).toBeVisible();
});

test("the contact list is a valid description list", async ({ page }) => {
  await page.goto("/");
  // A <dl> allows one <div> around each dt/dd pair, never two.
  await expect(page.locator("#contact dl > div > dt")).toHaveCount(3);
  await expect(page.locator("#contact dl > div > dd")).toHaveCount(3);
});

// One page per test: visiting /ar remembers the language, and a later visit
// to / in the same page would be sent on to /ar.
for (const path of ["/", "/ar"]) {
  test(`${path} links the monogram icons`, async ({ page }) => {
    await page.goto(path);
    for (const [rel, size] of [["icon", "32x32"], ["apple-touch-icon", "180x180"]]) {
      const link = page.locator(`link[rel="${rel}"][type="image/png"]`);
      await expect(link).toHaveCount(1);
      await expect(link).toHaveAttribute("sizes", size);
      const response = await page.request.get((await link.getAttribute("href"))!);
      expect(response.status()).toBe(200);
      // PNG signature: the file the export wrote, not a 404 page.
      expect([...(await response.body()).subarray(0, 4)]).toEqual([0x89, 0x50, 0x4e, 0x47]);
    }
    // Next also links app/favicon.ico, which the next test checks is the
    // monogram too. Any other icon would be one nobody meant to ship.
    const others = await page
      .locator('link[rel="icon"]:not([type="image/png"])')
      .evaluateAll((links) => links.map((link) => link.getAttribute("href")!));
    for (const href of others) expect(href).toMatch(/^\/favicon\.ico(\?|$)/);
  });
}

// What browsers, feed readers and crawlers fetch whatever a page links. The
// default favicon held four bitmaps; this is the 32px monogram app/icon.tsx
// draws, as one PNG in an .ico (scripts/build-favicon.mjs).
test("/favicon.ico is the monogram", async ({ page }) => {
  const response = await page.request.get("/favicon.ico");
  expect(response.status()).toBe(200);
  const ico = await response.body();
  // ICONDIR: reserved 0, type 1 (icon), one image.
  expect([ico.readUInt16LE(0), ico.readUInt16LE(2), ico.readUInt16LE(4)]).toEqual([0, 1, 1]);
  expect([ico[6], ico[7]]).toEqual([32, 32]);
  const offset = ico.readUInt32LE(18);
  expect(offset + ico.readUInt32LE(14)).toBe(ico.length);
  const png = ico.subarray(offset);
  expect([...png.subarray(0, 4)]).toEqual([0x89, 0x50, 0x4e, 0x47]);
  expect([png.readUInt32BE(16), png.readUInt32BE(20)]).toEqual([32, 32]);
});
