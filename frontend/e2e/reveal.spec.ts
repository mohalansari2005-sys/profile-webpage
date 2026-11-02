import { expect, test, type Page } from "@playwright/test";

// Scroll-revealed blocks ship at opacity 0. These cover the ways a reader can
// reach the page without ever scrolling them into view.
const hiddenReveals = (page: Page) =>
  page.evaluate(
    () =>
      [...document.querySelectorAll(".reveal")].filter(
        (el) => getComputedStyle(el).opacity !== "1",
      ).length,
  );

for (const path of ["/", "/ar"]) {
  test(`printing ${path} without scrolling shows every section`, async ({ page }) => {
    await page.goto(path);
    expect(await page.locator(".reveal").count()).toBeGreaterThan(10);
    // Printing straight away is the case that went blank: nothing below the
    // hero had been revealed yet.
    expect(await hiddenReveals(page)).toBeGreaterThan(0);
    await page.emulateMedia({ media: "print" });
    expect(await hiddenReveals(page)).toBe(0);
  });
}

test("with the app's script blocked, everything is still shown", async ({ page }) => {
  // JS stays on, so the <noscript> rule does not apply; only the watchdog in
  // site-head.tsx can show the page.
  await page.route("**/_next/static/chunks/*.js", (route) => route.abort());
  await page.goto("/");
  await expect(page.locator("html")).toHaveClass(/\breveal-fallback\b/, { timeout: 10_000 });
  await expect.poll(() => hiddenReveals(page)).toBe(0);
});

test("with the app running, the watchdog leaves the scroll reveal alone", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("data-reveal-ready", "");
  // Past the watchdog's two seconds after load.
  await page.waitForTimeout(2_500);
  await expect(page.locator("html")).not.toHaveClass(/\breveal-fallback\b/);
  const contact = page.locator("#contact .reveal").first();
  expect(await contact.evaluate((el) => getComputedStyle(el).opacity)).toBe("0");
  await contact.scrollIntoViewIfNeeded();
  await expect.poll(() => contact.evaluate((el) => getComputedStyle(el).opacity)).toBe("1");
});
