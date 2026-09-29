import { expect, test, type Page } from "@playwright/test";

// The page is still English; these tests flip it to RTL/Arabic in the browser to
// prove the CSS is direction-safe before any Arabic content exists.
async function goRtl(page: Page) {
  await page.goto("/");
  await page.evaluate(() => {
    document.documentElement.dir = "rtl";
    document.documentElement.lang = "ar";
  });
}

test("no horizontal overflow in RTL", async ({ page }) => {
  await goRtl(page);
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(0);
});

test("the hero rule draws from the right", async ({ page }) => {
  await goRtl(page);
  const { originX, width } = await page.locator(".rule-draw").evaluate((el) => ({
    originX: parseFloat(getComputedStyle(el).transformOrigin.split(" ")[0]),
    // offsetWidth, not getBoundingClientRect: the rule animates scaleX, and the
    // bounding box shrinks mid-animation while the origin stays in layout px.
    width: (el as HTMLElement).offsetWidth,
  }));
  expect(originX).toBeCloseTo(width, 0);
});

test("the About quote's rule moves to the right side", async ({ page }) => {
  await goRtl(page);
  const rule = await page.locator("#about blockquote").evaluate((el) => {
    const s = getComputedStyle(el);
    return { left: s.borderLeftWidth, right: s.borderRightWidth };
  });
  expect(rule).toEqual({ left: "0px", right: "2px" });
});

test("the row match marker sits on the start (right) edge", async ({ page }) => {
  await goRtl(page);
  const row = page.locator("#record-exp-majara");
  const marker = row.locator("> span").first();
  const [r, m] = [await row.boundingBox(), await marker.boundingBox()];
  expect(m!.x).toBeGreaterThan(r!.x + r!.width / 2);
});

test("Arabic text gets no letter-spacing on labels", async ({ page }) => {
  await goRtl(page);
  const spacing = await page
    .locator("#about .field-label")
    .evaluate((el) => getComputedStyle(el).letterSpacing);
  expect(["normal", "0px"]).toContain(spacing);
});

test("tool strip fades swap sides in RTL", async ({ page }) => {
  await page.goto("/");
  // Chrome reports `to right` as 90deg and `to left` as 270deg.
  const mask = () =>
    page.evaluate(() => {
      const el = document.createElement("div");
      el.className = "tool-strip";
      el.dataset.edge = "end";
      document.body.appendChild(el);
      const m = getComputedStyle(el).maskImage;
      el.remove();
      return m;
    });
  expect(await mask()).toContain("90deg");
  await page.evaluate(() => (document.documentElement.dir = "rtl"));
  expect(await mask()).toContain("270deg");
});

test("project chevrons page toward the end in RTL", async ({ page }) => {
  await goRtl(page);
  await page.evaluate(() => {
    const rail = document.querySelector("[data-project-rail]")!;
    for (let i = 0; i < 4; i++) {
      const clone = rail.firstElementChild!.cloneNode(true) as HTMLElement;
      clone.querySelector("article")!.removeAttribute("id");
      rail.appendChild(clone);
    }
    window.dispatchEvent(new Event("resize"));
  });
  const next = page.getByRole("button", { name: "Next project" });
  const prev = page.getByRole("button", { name: "Previous project" });
  await next.scrollIntoViewIfNeeded();
  await expect(prev).toBeDisabled();
  await expect(next).toBeEnabled();

  await next.click();
  const rail = page.locator("[data-project-rail]");
  // RTL scrollLeft goes negative; "next" must travel that way and enable prev.
  await expect.poll(() => rail.evaluate((el) => el.scrollLeft)).toBeLessThan(-100);
  await expect(prev).toBeEnabled();
});
