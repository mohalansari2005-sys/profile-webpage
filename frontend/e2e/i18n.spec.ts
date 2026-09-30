import { expect, test, type Page } from "@playwright/test";

const CHAT_API = "http://chat.test/api/chat/";

async function ask(page: Page, question: string) {
  await page.locator("#ask-input").fill(question);
  await page.getByRole("button", { name: "إرسال السؤال" }).click();
}

test.describe("Arabic page", () => {
  test("is Arabic and right-to-left from the first byte of HTML", async ({ page }) => {
    const response = await page.request.get("/ar");
    const html = await response.text();
    expect(html).toMatch(/<html[^>]*lang="ar"[^>]*dir="rtl"/);
    await page.goto("/ar");
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
    await expect(page).toHaveTitle("محمد الأنصاري");
  });

  test("every section is in Arabic", async ({ page }) => {
    await page.goto("/ar");
    await expect(page.locator("h1")).toContainText("محمد");
    for (const name of ["نبذة", "الخبرة", "المشاريع", "تواصل"]) {
      await expect(page.getByRole("heading", { level: 2, name, exact: true })).toBeVisible();
    }
    await expect(
      page.getByRole("heading", { level: 2, name: "اسأل مساعدي الذكي عن أعمالي." }),
    ).toBeVisible();
  });

  test("has no horizontal overflow", async ({ page }) => {
    await page.goto("/ar");
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow).toBeLessThanOrEqual(0);
  });

  test("uses the Arabic typeface, English keeps its own", async ({ page }) => {
    const family = (sel: string) =>
      page.locator(sel).first().evaluate((el) => getComputedStyle(el).fontFamily);
    // English first: visiting /ar remembers Arabic, which would send a later
    // visit to `/` back to /ar.
    await page.goto("/");
    expect(await family("h1")).not.toMatch(/IBM_Plex_Sans_Arabic|IBM Plex Sans Arabic/);
    await page.goto("/ar");
    expect(await family("h1")).toMatch(/IBM_Plex_Sans_Arabic|IBM Plex Sans Arabic/);
  });

  test("translates the work records and the project link", async ({ page }) => {
    await page.goto("/ar");
    const row = page.locator("#record-exp-majara");
    await expect(row).toContainText("متدرب هندسة منتجات");
    await expect(row).toContainText("نوفمبر 2025 — الآن");
    await expect(page.getByRole("link", { name: "Keyraa على GitHub" })).toHaveAttribute(
      "href",
      "https://github.com/mohalansari2005-sys/keyraa-hotel-booking",
    );
  });

  test("the theme toggle speaks Arabic", async ({ page }) => {
    await page.goto("/ar");
    await expect(page.getByRole("button", { name: /^المظهر:/ })).toHaveAttribute(
      "aria-label",
      "المظهر: النظام. التبديل إلى فاتح.",
    );
  });

  test("the language switch is an icon, not text", async ({ page }) => {
    await page.goto("/");
    const link = page.getByRole("link", { name: "Switch to Arabic" });
    await expect(link).toHaveText("");
    expect(await link.locator("svg").getAttribute("class")).toContain("lucide-languages");
  });

  test("declares its language alternates for search engines", async ({ page }) => {
    await page.goto("/ar");
    await expect(page.locator('link[rel="alternate"][hreflang="en"]')).toHaveCount(1);
    await expect(page.locator('link[rel="alternate"][hreflang="ar"]')).toHaveCount(1);
    await expect(page.locator('meta[property="og:image"]')).toHaveCount(1);
  });
});

test.describe("chat in Arabic", () => {
  test("mirrors the sides: questions start on the left", async ({ page }) => {
    await page.route(CHAT_API, (route) =>
      route.fulfill({ json: { answer: "إجابة قصيرة.", sources: [], refused: false } }),
    );
    await page.goto("/ar");
    await ask(page, "ما هي ماجرة؟");
    const answer = page.getByText("إجابة قصيرة.");
    await expect(answer).toBeVisible();
    const q = await page.getByText("ما هي ماجرة؟").last().boundingBox();
    const a = await answer.boundingBox();
    expect(q!.x + q!.width / 2).toBeLessThan(a!.x + a!.width / 2);
  });

  test("source chips show the Arabic title", async ({ page }) => {
    await page.route(CHAT_API, (route) =>
      route.fulfill({
        json: {
          answer: "إجابة.",
          sources: [{ record_id: "exp-majara", title: "Product Engineering Intern" }],
          refused: false,
        },
      }),
    );
    await page.goto("/ar");
    await ask(page, "ماذا فعل؟");
    await expect(page.getByRole("button", { name: /متدرب هندسة منتجات/ })).toBeVisible();
    await expect(page.getByText("Product Engineering Intern")).toHaveCount(0);
  });

  test("errors are shown in Arabic", async ({ page }) => {
    await page.route(CHAT_API, (route) => route.fulfill({ status: 500, body: "boom" }));
    await page.goto("/ar");
    await ask(page, "سؤال");
    await expect(page.getByText("واجهت خدمة الإجابة خطأً. حاول بعد قليل.")).toBeVisible();
  });

  test("the English page still shows English errors", async ({ page }) => {
    await page.route(CHAT_API, (route) => route.fulfill({ status: 500, body: "boom" }));
    await page.goto("/");
    await page.locator("#ask-input").fill("question");
    await page.getByRole("button", { name: "Send question" }).click();
    await expect(page.getByText("The answer service hit an error. Try again in a moment.")).toBeVisible();
  });
});

test.describe("switching language", () => {
  test("toggles between the two pages", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Switch to Arabic" }).click();
    await expect(page).toHaveURL(/\/ar\/?$/);
    await expect(page.locator("html")).toHaveAttribute("lang", "ar");

    await page.getByRole("link", { name: "التبديل إلى الإنجليزية" }).click();
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    await expect(page).toHaveURL(/\/$/);
  });

  test("keeps the #section", async ({ page }) => {
    await page.goto("/#about");
    await page.getByRole("link", { name: "Switch to Arabic" }).click();
    await expect(page).toHaveURL(/\/ar\/?#about$/);
  });

  test("the link itself carries the #section and the choice", async ({ page }) => {
    // Middle-click / "open in new tab" never fire a click handler, so the href
    // must already hold everything.
    await page.goto("/#about");
    await expect(page.getByRole("link", { name: "Switch to Arabic" })).toHaveAttribute(
      "href",
      "/ar#about",
    );
    await page.goto("/ar#work");
    await expect(page.getByRole("link", { name: "التبديل إلى الإنجليزية" })).toHaveAttribute(
      "href",
      "/?lang=en#work",
    );
  });

  test("opening the English link directly (not clicking) still remembers English", async ({
    page,
    context,
  }) => {
    await page.goto("/ar"); // visiting /ar remembers Arabic
    const href = await page
      .getByRole("link", { name: "التبديل إلى الإنجليزية" })
      .getAttribute("href");

    const tab = await context.newPage();
    await tab.goto(href!);
    await expect(tab.locator("html")).toHaveAttribute("lang", "en");
    await expect(tab).toHaveURL(/\/$/); // ?lang=en cleaned from the URL

    await tab.goto("/"); // no bounce back to /ar
    await expect(tab.locator("html")).toHaveAttribute("lang", "en");
    await expect(tab).toHaveURL(/\/$/);
  });

  test("visiting /ar directly remembers Arabic", async ({ page }) => {
    await page.goto("/ar");
    await page.goto("/");
    await expect(page).toHaveURL(/\/ar\/?$/);
  });

  test("remembers Arabic when the reader returns to /", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Switch to Arabic" }).click();
    await expect(page.locator("html")).toHaveAttribute("lang", "ar");

    await page.goto("/");
    await expect(page).toHaveURL(/\/ar\/?$/);

    // ...and choosing English again stops the redirect.
    await page.getByRole("link", { name: "التبديل إلى الإنجليزية" }).click();
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    await page.goto("/");
    await expect(page).toHaveURL(/\/$/);
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
  });

  test("a first-time visitor to / is not redirected", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/$/);
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
  });
});
