import { expect, test } from "@playwright/test";

// Phone and iPad sizes, each on both language pages. The first bug this guards
// against: on a phone the page was wider than the screen (scrollWidth 643 on a
// 390px viewport) because the chat's no-wrap suggestion row stretched an
// unbounded grid column.
const SIZES = [
  { name: "small phone", width: 320, height: 640, klass: "phone" },
  { name: "iPhone SE", width: 375, height: 667, klass: "phone" },
  { name: "iPhone 14", width: 390, height: 844, klass: "phone" },
  { name: "large phone", width: 430, height: 932, klass: "phone" },
  { name: "iPad mini portrait", width: 744, height: 1133, klass: "tablet" },
  { name: "iPad Air portrait", width: 820, height: 1180, klass: "tablet" },
  { name: "iPad Pro 11 portrait", width: 834, height: 1194, klass: "tablet" },
  { name: "iPad landscape", width: 1024, height: 768, klass: "desktop" },
] as const;

for (const size of SIZES) {
  for (const path of ["/", "/ar"]) {
    test.describe(`${size.name} (${size.width}px) ${path}`, () => {
      test.use({ viewport: { width: size.width, height: size.height }, hasTouch: true });

      test("is never wider than the screen", async ({ page }) => {
        await page.goto(path);
        const { client, scroll } = await page.evaluate(() => ({
          client: document.documentElement.clientWidth,
          scroll: document.documentElement.scrollWidth,
        }));
        expect(scroll).toBeLessThanOrEqual(client);
      });

      test("uses the right page gutter", async ({ page }) => {
        await page.goto(path);
        const gutter = await page
          .locator("#about > div")
          .evaluate((el) => parseFloat(getComputedStyle(el).paddingInlineStart));
        // 24px on phones and once desktop/iPad-landscape centres the column;
        // 40px on iPad portrait.
        expect(gutter).toBe(size.klass === "tablet" ? 40 : 24);
      });

      test("puts the section label beside its content only from 640px", async ({ page }) => {
        await page.goto(path);
        const [label, body] = await Promise.all([
          page.locator("#about h2").boundingBox(),
          page.locator("#about p").first().boundingBox(),
        ]);
        if (size.klass === "phone") {
          expect(label!.y + label!.height).toBeLessThanOrEqual(body!.y); // stacked
        } else {
          expect(Math.abs(label!.y - body!.y)).toBeLessThan(30); // side by side
        }
      });
    });
  }
}

test.describe("phone specifics", () => {
  test.use({ viewport: { width: 390, height: 844 }, hasTouch: true });

  test("the pinned 'Built with' bar stays on one line", async ({ page }) => {
    await page.goto("/");
    const heights = await page.evaluate(() => {
      const bar = document.querySelector("#work > div") as HTMLElement;
      return {
        label: (bar.querySelector("h2") as HTMLElement).getBoundingClientRect().height,
        hint: (bar.querySelector("p") as HTMLElement).getBoundingClientRect().height,
      };
    });
    expect(heights.label).toBeLessThan(24);
    expect(heights.hint).toBeLessThan(24);
  });

  test("the chat box is phone-sized and its suggestions wrap inside it", async ({ page }) => {
    await page.goto("/");
    const box = page.locator("#ask .rounded-3xl");
    const b = await box.boundingBox();
    expect(b!.width).toBeLessThanOrEqual(390);
    expect(b!.height).toBeLessThanOrEqual(544 + 1);
    const chips = page.locator("#ask button", { hasText: "What did he build at Majara?" });
    const c = await chips.boundingBox();
    expect(c!.x + c!.width).toBeLessThanOrEqual(b!.x + b!.width);
  });
});

test.describe("touch targets", () => {
  // Chrome's device emulation reports (pointer: coarse), which is what the
  // `pointer-coarse:` variants key off.
  test.use({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 3,
    isMobile: true,
    hasTouch: true,
  });

  test("controls are finger-sized on a phone", async ({ page }) => {
    await page.goto("/");
    const size = async (selector: string) =>
      (await page.locator(selector).first().boundingBox())!;
    const theme = await size('button[aria-label^="Theme:"]');
    expect(Math.min(theme.width, theme.height)).toBeGreaterThanOrEqual(44);
    const lang = await size('a[aria-label="Switch to Arabic"]');
    expect(Math.min(lang.width, lang.height)).toBeGreaterThanOrEqual(44);
    const next = await size('button[aria-label="Next project"]');
    expect(Math.min(next.width, next.height)).toBeGreaterThanOrEqual(44);
    const tool = await size('#work button[aria-pressed]');
    expect(tool.height).toBeGreaterThanOrEqual(38);
  });
});

test.describe("chat height follows the device", () => {
  const boxHeight = async (page: import("@playwright/test").Page) =>
    (await page.locator("#ask .rounded-3xl").boundingBox())!.height;

  test("taller on an iPad than on a phone or a laptop", async ({ browser }) => {
    const heightAt = async (width: number, height: number) => {
      const ctx = await browser.newContext({ viewport: { width, height } });
      const page = await ctx.newPage();
      await page.goto("/");
      const h = await boxHeight(page);
      await ctx.close();
      return h;
    };
    const phone = await heightAt(390, 844);
    const ipad = await heightAt(820, 1180);
    const laptop = await heightAt(1280, 720);
    expect(ipad).toBeGreaterThan(phone);
    expect(ipad).toBeGreaterThan(laptop);
  });
});
