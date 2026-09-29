import { expect, test, type Page } from "@playwright/test";

// Only one project exists today, so a rail that scrolls needs more cards. The
// tests clone the real card in the browser and nudge the rail to re-measure
// (it listens for resize). Clones lose their ids so #record-* stays unique.
async function withMoreCards(page: Page, extra = 4) {
  await page.evaluate((count) => {
    const rail = document.querySelector("[data-project-rail]")!;
    const first = rail.firstElementChild as HTMLElement;
    for (let i = 0; i < count; i++) {
      const clone = first.cloneNode(true) as HTMLElement;
      clone.querySelector("article")!.removeAttribute("id");
      rail.appendChild(clone);
    }
    window.dispatchEvent(new Event("resize"));
  }, extra);
}

// Paging is a smooth scroll; wait until scrollLeft stops moving so button
// state is read after the rail has arrived, not mid-flight.
async function settle(page: Page) {
  const rail = page.locator("[data-project-rail]");
  let last = -1;
  await expect
    .poll(async () => {
      const now = await rail.evaluate((el) => el.scrollLeft);
      const stable = now === last;
      last = now;
      return stable;
    }, { intervals: [150] })
    .toBe(true);
}

test("a project links to its GitHub repo", async ({ page }) => {
  await page.goto("/");
  const link = page.getByRole("link", { name: "Keyraa on GitHub" });
  await expect(link).toHaveAttribute(
    "href",
    "https://github.com/mohalansari2005-sys/keyraa-hotel-booking",
  );
  await expect(link).toHaveAttribute("target", "_blank");
  await expect(link).toHaveAttribute("rel", /noopener/);
});

test("projects are rounded cards in a horizontal rail", async ({ page }) => {
  await page.goto("/");
  const card = page.locator("[data-project-rail] article").first();
  expect(await card.evaluate((el) => getComputedStyle(el).borderTopLeftRadius)).not.toBe("0px");
  const rail = page.locator("[data-project-rail]");
  expect(await rail.evaluate((el) => getComputedStyle(el).overflowX)).toBe("auto");
});

test("with one project both chevrons are disabled", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Previous project" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Next project" })).toBeDisabled();
});

test("chevrons page the rail and disable at the ends", async ({ page }) => {
  await page.goto("/");
  await withMoreCards(page);
  const prev = page.getByRole("button", { name: "Previous project" });
  const next = page.getByRole("button", { name: "Next project" });
  const rail = page.locator("[data-project-rail]");

  await expect(next).toBeEnabled();
  await expect(prev).toBeDisabled();

  await next.click();
  await settle(page);
  expect(await rail.evaluate((el) => Math.abs(el.scrollLeft))).toBeGreaterThan(100);
  await expect(prev).toBeEnabled();

  for (let i = 0; i < 8; i++) {
    if (await next.isDisabled()) break;
    await next.click();
    await settle(page);
  }
  await expect(next).toBeDisabled();

  await prev.click();
  await settle(page);
  await expect(next).toBeEnabled();
});

test("the rail scrolls sideways without moving the page down", async ({ page }) => {
  await page.goto("/");
  await withMoreCards(page);
  // The chevrons sit above the rail; bring the one we click on screen first, or
  // Playwright's own scroll-to-click would be counted as the page moving.
  const next = page.getByRole("button", { name: "Next project" });
  await next.scrollIntoViewIfNeeded();
  const before = await page.evaluate(() => scrollY);
  await next.click();
  await settle(page);
  expect(Math.abs((await page.evaluate(() => scrollY)) - before)).toBeLessThan(5);
});
