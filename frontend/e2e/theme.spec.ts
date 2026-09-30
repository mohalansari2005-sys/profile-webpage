import { expect, test } from "@playwright/test";

const DARK_BG = "rgb(15, 22, 38)"; // --surface-base in dark
const LIGHT_BG = "rgb(235, 238, 243)"; // --surface-base in light

const bodyBg = (page: import("@playwright/test").Page) =>
  page.evaluate(() => getComputedStyle(document.body).backgroundColor);

test.describe("OS prefers dark", () => {
  test.use({ colorScheme: "dark" });

  test("follows the system with nothing stored", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("html")).toHaveClass(/\bdark\b/);
    expect(await bodyBg(page)).toBe(DARK_BG);
  });

  test("an explicit light choice beats the OS", async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem("theme", "light"));
    await page.goto("/");
    await expect(page.locator("html")).not.toHaveClass(/\bdark\b/);
    expect(await bodyBg(page)).toBe(LIGHT_BG);
  });

  test("the Projects section stays distinct from the page", async ({ page }) => {
    await page.goto("/");
    const deep = await page
      .locator("section.on-deep")
      .evaluate((el) => getComputedStyle(el).backgroundColor);
    expect(deep).not.toBe(await bodyBg(page));
  });
});

test.describe("OS prefers dark, script blocked", () => {
  test.use({ colorScheme: "dark", javaScriptEnabled: false });

  test("the CSS fallback still goes dark", async ({ page }) => {
    await page.goto("/");
    expect(await bodyBg(page)).toBe(DARK_BG);
  });
});

test.describe("toggle", () => {
  test.use({ colorScheme: "light" });

  const toggle = (page: import("@playwright/test").Page) =>
    page.getByRole("button", { name: /^Theme:/ });
  // lucide renders <svg class="lucide lucide-sun ...">.
  const iconOf = (page: import("@playwright/test").Page) =>
    toggle(page).locator("svg").getAttribute("class");

  test("is an icon (monitor, sun, moon) with a full accessible name", async ({ page }) => {
    await page.goto("/");
    await expect(toggle(page)).toHaveText(""); // no visible text, icon only
    await expect(toggle(page)).toHaveAttribute("aria-label", "Theme: System. Switch to Light.");
    expect(await iconOf(page)).toContain("lucide-monitor");

    await toggle(page).click();
    await expect(toggle(page)).toHaveAttribute("aria-label", "Theme: Light. Switch to Dark.");
    expect(await iconOf(page)).toContain("lucide-sun");

    await toggle(page).click();
    await expect(toggle(page)).toHaveAttribute("aria-label", "Theme: Dark. Switch to System.");
    expect(await iconOf(page)).toContain("lucide-moon");
  });

  test("cycles system -> light -> dark -> system and persists", async ({ page }) => {
    await page.goto("/");
    await expect(toggle(page)).toHaveAttribute("data-mode", "system");

    await toggle(page).click();
    await expect(toggle(page)).toHaveAttribute("data-mode", "light");
    await expect(page.locator("html")).toHaveClass(/\blight\b/);

    await toggle(page).click();
    await expect(toggle(page)).toHaveAttribute("data-mode", "dark");
    await expect(page.locator("html")).toHaveClass(/\bdark\b/);
    expect(await bodyBg(page)).toBe(DARK_BG);

    await page.reload();
    await expect(page.locator("html")).toHaveClass(/\bdark\b/);
    await expect(toggle(page)).toHaveAttribute("data-mode", "dark");

    await toggle(page).click();
    await expect(toggle(page)).toHaveAttribute("data-mode", "system");
    await expect(page.locator("html")).not.toHaveClass(/\bdark\b/);
    expect(await page.evaluate(() => localStorage.getItem("theme"))).toBeNull();
  });
});
