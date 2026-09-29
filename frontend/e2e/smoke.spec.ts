import { expect, test } from "@playwright/test";

// The chat API URL is baked in at build time (see CI), and every request to it
// is intercepted here, so these tests never touch a real backend or OpenAI.
const CHAT_API = "http://chat.test/api/chat/";

test("renders every section", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("h1")).toBeVisible();
  for (const name of ["About", "Experience", "Projects", "Ask", "Contact"]) {
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
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await expect(page.getByText("Mocked answer about Mohammed.")).toBeVisible();
});
