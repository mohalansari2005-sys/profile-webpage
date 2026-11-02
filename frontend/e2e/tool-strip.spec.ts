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

// The chip nearest the strip's end edge that is still partly visible: half
// under the fade, where a reader presses the half they can see.
async function chipUnderFade(page: Page) {
  await page.evaluate(() =>
    document.getElementById("work")!.scrollIntoView({ behavior: "instant" }),
  );
  return strip(page).evaluate((el) => {
    const s = el.getBoundingClientRect();
    const chip = [...el.querySelectorAll("button")].find((b) => {
      const r = b.getBoundingClientRect();
      return r.left < s.right - 10 && r.right > s.right - 48;
    })!;
    const r = chip.getBoundingClientRect();
    return { label: chip.textContent!, x: Math.min(r.right, s.right) - 4, y: r.top + r.height / 2 };
  });
}

// Chrome focuses a button on mousedown, and Android Chrome on a tap. Scrolling
// the strip on that focus slid the chip away before mouseup, so the press
// landed between two chips and nothing was pinned.
async function expectPinned(page: Page, label: string) {
  await expect(strip(page).getByRole("button", { name: label, exact: true })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await expect(page.locator("#work p[aria-live]")).toContainText(label);
}

test.describe("at 1280px with a mouse", () => {
  test.use({ viewport: { width: 1280, height: 800 } });

  test("clicking a chip half under the fade pins it", async ({ page }) => {
    await page.goto("/");
    const { label, x, y } = await chipUnderFade(page);
    await page.mouse.move(x, y);
    await page.mouse.click(x, y, { delay: 80 });
    await expectPinned(page, label);
  });
});

test.describe("on a touch phone", () => {
  test.use({ viewport: { width: 412, height: 839 }, hasTouch: true, isMobile: true });

  test("tapping a chip half under the fade pins it", async ({ page }) => {
    await page.goto("/");
    const { label, x, y } = await chipUnderFade(page);
    await page.touchscreen.tap(x, y);
    await expectPinned(page, label);
  });
});

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
