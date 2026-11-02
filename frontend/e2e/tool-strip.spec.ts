import { expect, test, type Page } from "@playwright/test";
import { en } from "../messages/en";

const strip = (page: Page) => page.locator(".tool-strip");
const chips = (page: Page) => strip(page).getByRole("button");

for (const width of [1280, 390]) {
  test.describe(`at ${width}px`, () => {
    test.use({ viewport: { width, height: 800 } });

    test("Clear shows on screen once a tool is pinned", async ({ page }) => {
      await page.goto("/");
      await chips(page).first().click();
      // It used to sit at the end of the strip, 1,400px or more out of view.
      await expect(page.getByRole("button", { name: en.work.clear })).toBeInViewport({ ratio: 1 });
    });
  });
}

test("Clear hands keyboard focus to the strip, without lighting a tool", async ({ page }) => {
  await page.goto("/");
  await chips(page).first().focus();
  await page.keyboard.press("Enter");
  await expect(chips(page).first()).toHaveAttribute("aria-pressed", "true");
  const clear = page.getByRole("button", { name: en.work.clear });
  await clear.focus();
  await page.keyboard.press("Enter");
  await expect(clear).toHaveCount(0);
  await expect(page.getByRole("heading", { name: en.work.builtWith })).toBeFocused();
  await expect(page.locator('#work [data-state="lit"]')).toHaveCount(0);
  // ...and the next Tab carries on into the strip.
  await page.keyboard.press("Tab");
  await expect(chips(page).first()).toBeFocused();
});

test.describe("on a phone", () => {
  test.use({ viewport: { width: 375, height: 812 }, hasTouch: true });

  for (const path of ["/", "/ar"]) {
    test(`tabbing through the strip on ${path} keeps each chip fully in view`, async ({ page }) => {
      await page.goto(path);
      await chips(page).first().focus();
      const count = await chips(page).count();
      for (let i = 0; i < count; i++) {
        const focused = page.locator(".tool-strip button:focus");
        const [s, c] = [await strip(page).boundingBox(), await focused.boundingBox()];
        const label = (await focused.textContent()) ?? "";
        expect(c!.x, label).toBeGreaterThanOrEqual(s!.x - 1);
        expect(c!.x + c!.width, label).toBeLessThanOrEqual(s!.x + s!.width + 1);
        await page.keyboard.press("Tab");
      }
    });
  }
});
