import { expect, test, type Page } from "@playwright/test";
import { experience } from "../lib/content";
import { format } from "../lib/i18n";
import { ar } from "../messages/ar";

// Assertions read the same dictionaries and content the site renders, so
// rewording the Arabic copy never needs a test edit; the tests check that the
// right strings land in the right places.
const majara = experience.find((r) => r.id === "exp-majara")!;

const CHAT_API = "http://chat.test/api/chat/";

async function ask(page: Page, question: string) {
  await page.locator("#ask-input").fill(question);
  await page.getByRole("button", { name: ar.ask.send }).click();
}

test.describe("Arabic page", () => {
  test("is Arabic and right-to-left from the first byte of HTML", async ({ page }) => {
    const response = await page.request.get("/ar");
    const html = await response.text();
    expect(html).toMatch(/<html[^>]*lang="ar"[^>]*dir="rtl"/);
    await page.goto("/ar");
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
    await expect(page).toHaveTitle(ar.meta.title);
  });

  test("every section is in Arabic", async ({ page }) => {
    await page.goto("/ar");
    await expect(page.locator("h1")).toContainText(ar.hero.nameFirst);
    for (const name of [ar.about.label, ar.work.experience, ar.work.projects, ar.contact.label]) {
      await expect(page.getByRole("heading", { level: 2, name, exact: true })).toBeVisible();
    }
    await expect(
      page.getByRole("heading", { level: 2, name: ar.ask.heading }),
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

  // The computed family string looked right while the glyphs came from Arial,
  // so this asks Chrome which fonts actually drew the text. (Linux has no
  // Arial, so only a macOS or Windows run can catch the regression.)
  test("mono labels draw Arabic letters in Plex, not a system fallback", async ({ page }) => {
    await page.goto("/ar");
    await page.evaluate(() => document.fonts.ready);
    const cdp = await page.context().newCDPSession(page);
    await cdp.send("DOM.enable");
    await cdp.send("CSS.enable");
    const { root } = await cdp.send("DOM.getDocument");
    for (const selector of ["#about .field-label", "#work p[aria-live]"]) {
      const { nodeId } = await cdp.send("DOM.querySelector", { nodeId: root.nodeId, selector });
      const { fonts } = await cdp.send("CSS.getPlatformFontsForNode", { nodeId });
      const names = fonts.map((font) => font.familyName);
      expect(names.some((name) => /Plex/i.test(name)), `${selector}: ${names}`).toBe(true);
      expect(names.some((name) => /Arial/i.test(name)), `${selector}: ${names}`).toBe(false);
    }
  });

  test("the English page does not preload the Arabic typeface", async ({ page }) => {
    const html = await (await page.request.get("/")).text();
    const preloads = [...html.matchAll(/<link rel="preload" href="([^"]+\.woff2)"/g)].map(
      (match) => match[1].split("/").pop(),
    );
    expect(preloads.length).toBeGreaterThan(0);
    const plexFiles: string[] = [];
    for (const [, href] of html.matchAll(/<link rel="stylesheet" href="([^"]+\.css)"/g)) {
      const css = await (await page.request.get(href)).text();
      for (const [, url] of css.matchAll(
        /@font-face\s*\{[^}]*font-family:\s*["']?IBM Plex Sans Arabic["']?;[^}]*url\(([^)]+)\)/g,
      )) {
        plexFiles.push(url.split("/").pop()!);
      }
    }
    expect(plexFiles.length).toBeGreaterThan(0);
    expect(preloads.filter((file) => plexFiles.includes(file!))).toEqual([]);
  });

  test("translates the work records and the project link", async ({ page }) => {
    await page.goto("/ar");
    const row = page.locator("#record-exp-majara");
    await expect(row).toContainText(majara.ar!.title!);
    await expect(row).toContainText(majara.ar!.period!);
    await expect(page.getByRole("link", { name: format(ar.work.onGithub, { title: "Keyraa" }) })).toHaveAttribute(
      "href",
      "https://github.com/mohalansari2005-sys/keyraa-hotel-booking",
    );
  });

  test("the theme toggle speaks Arabic", async ({ page }) => {
    await page.goto("/ar");
    await expect(page.locator("button[data-mode]")).toHaveAttribute(
      "aria-label",
      format(ar.theme.aria, { current: ar.theme.system, next: ar.theme.light }),
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

  // The domain is a literal on purpose: built from site-metadata.ts, this
  // would still pass if metadataBase went back to a *.vercel.app alias.
  // One page per test: visiting /ar remembers the language, and a later visit
  // to / in the same page would be sent on to /ar.
  const SITE = "https://www.alansari.stream";
  for (const [path, canonical] of [["/", SITE], ["/ar", `${SITE}/ar`]]) {
    test(`${path} points search engines and link previews at the custom domain`, async ({ page }) => {
      await page.goto(path);
      await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", canonical);
      await expect(page.locator('meta[property="og:url"]')).toHaveAttribute("content", canonical);
      for (const [lang, href] of [["en", SITE], ["ar", `${SITE}/ar`], ["x-default", SITE]]) {
        await expect(page.locator(`link[rel="alternate"][hreflang="${lang}"]`))
          .toHaveAttribute("href", href);
      }
      await expect(page.locator('meta[property="og:image"]'))
        .toHaveAttribute("content", `${SITE}/opengraph-image`);
      await expect(page.locator('meta[property="og:image:type"]')).toHaveAttribute("content", "image/png");
      await expect(page.locator('meta[name="twitter:image"]'))
        .toHaveAttribute("content", `${SITE}/opengraph-image`);
    });
  }
});

test.describe("chat in Arabic", () => {
  test("mirrors the sides: questions start on the left", async ({ page }) => {
    await page.route(CHAT_API, (route) =>
      route.fulfill({ json: { answer: "إجابة قصيرة.", sources: [], refused: false } }),
    );
    await page.goto("/ar");
    await ask(page, "وش هي مجرة؟");
    const answer = page.getByText("إجابة قصيرة.");
    await expect(answer).toBeVisible();
    const q = await page.getByText("وش هي مجرة؟").last().boundingBox();
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
    await expect(page.getByRole("button", { name: new RegExp(majara.ar!.title!) })).toBeVisible();
    await expect(page.getByText("Product Engineering Intern")).toHaveCount(0);
  });

  test("the empty input follows the page, typed text its own direction", async ({ page }) => {
    await page.goto("/ar");
    const input = page.locator("#ask-input");
    const direction = () => input.evaluate((el) => getComputedStyle(el).direction);
    expect(await direction()).toBe("rtl");
    await input.fill("What is Keyraa?");
    expect(await direction()).toBe("ltr");
    await input.fill("");
    expect(await direction()).toBe("rtl");
  });

  test("errors are shown in Arabic", async ({ page }) => {
    await page.route(CHAT_API, (route) => route.fulfill({ status: 500, body: "boom" }));
    await page.goto("/ar");
    await ask(page, "سؤال");
    await expect(page.getByText(ar.ask.errors.server)).toBeVisible();
  });

  test("the daily cap is explained in Arabic", async ({ page }) => {
    await page.route(CHAT_API, (route) =>
      route.fulfill({ status: 429, json: { detail: "Request was throttled.", code: "daily_cap" } }),
    );
    await page.goto("/ar");
    await ask(page, "سؤال");
    await expect(page.getByText(ar.ask.errors.dailyCap)).toBeVisible();
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

    await page.getByRole("link", { name: ar.lang.switchAria }).click();
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
    await expect(page.getByRole("link", { name: ar.lang.switchAria })).toHaveAttribute(
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
      .getByRole("link", { name: ar.lang.switchAria })
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
    await page.getByRole("link", { name: ar.lang.switchAria }).click();
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
