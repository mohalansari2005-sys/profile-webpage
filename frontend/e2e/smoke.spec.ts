import { expect, test } from "@playwright/test";

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
  test(`${path} links the monogram icons, not the default favicon`, async ({ page }) => {
    await page.goto(path);
    await expect(page.locator('link[href*="favicon"]')).toHaveCount(0);
    for (const [rel, size] of [["icon", "32x32"], ["apple-touch-icon", "180x180"]]) {
      const link = page.locator(`link[rel="${rel}"]`);
      await expect(link).toHaveCount(1);
      await expect(link).toHaveAttribute("type", "image/png");
      await expect(link).toHaveAttribute("sizes", size);
      const response = await page.request.get((await link.getAttribute("href"))!);
      expect(response.status()).toBe(200);
      // PNG signature: the file the export wrote, not a 404 page.
      expect([...(await response.body()).subarray(0, 4)]).toEqual([0x89, 0x50, 0x4e, 0x47]);
    }
  });
}
