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

  test("cycles system -> light -> dark -> system and persists", async ({ page }) => {
    await page.goto("/");
    const toggle = page.getByRole("button", { name: /^Theme:/ });
    await expect(toggle).toHaveText("Theme: System");

    await toggle.click();
    await expect(toggle).toHaveText("Theme: Light");
    await expect(page.locator("html")).toHaveClass(/\blight\b/);

    await toggle.click();
    await expect(toggle).toHaveText("Theme: Dark");
    await expect(page.locator("html")).toHaveClass(/\bdark\b/);
    expect(await bodyBg(page)).toBe(DARK_BG);

    await page.reload();
    await expect(page.locator("html")).toHaveClass(/\bdark\b/);
    await expect(page.getByRole("button", { name: /^Theme:/ })).toHaveText(
      "Theme: Dark",
    );

    await page.getByRole("button", { name: /^Theme:/ }).click();
    await expect(page.getByRole("button", { name: /^Theme:/ })).toHaveText(
      "Theme: System",
    );
    await expect(page.locator("html")).not.toHaveClass(/\bdark\b/);
    expect(await page.evaluate(() => localStorage.getItem("theme"))).toBeNull();
  });
});
