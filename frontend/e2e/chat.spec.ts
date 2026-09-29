import { expect, test, type Page } from "@playwright/test";

const CHAT_API = "http://chat.test/api/chat/";

const LONG = Array.from({ length: 40 }, (_, i) => `Sentence ${i + 1} about the work.`).join(" ");

function mock(page: Page, answer: string, sources: { record_id: string; title: string }[] = []) {
  return page.route(CHAT_API, (route) =>
    route.fulfill({ json: { answer, sources, refused: false } }),
  );
}

async function ask(page: Page, question: string) {
  await page.locator("#ask-input").fill(question);
  await page.getByRole("button", { name: "Ask", exact: true }).click();
}

const scroller = (page: Page) => page.locator('#ask [role="log"] > div').first();

test("questions sit on the right, answers on the left", async ({ page }) => {
  await mock(page, "A short answer.");
  await page.goto("/");
  await ask(page, "What does he do?");
  const q = page.getByText("What does he do?").last();
  const a = page.getByText("A short answer.");
  await expect(a).toBeVisible();
  const [qb, ab] = [await q.boundingBox(), await a.boundingBox()];
  expect(qb!.x + qb!.width / 2).toBeGreaterThan(ab!.x + ab!.width / 2);
});

test("a new answer scrolls the box, not the page", async ({ page }) => {
  await mock(page, LONG);
  await page.goto("/");
  await page.locator("#ask").scrollIntoViewIfNeeded();
  for (const q of ["one?", "two?", "three?"]) {
    await ask(page, q);
    await expect(page.getByText("Sentence 1 about")).toHaveCount(
      ["one?", "two?", "three?"].indexOf(q) + 1,
    );
  }
  const before = await page.evaluate(() => scrollY);
  await ask(page, "four?");
  await expect(page.getByText("Sentence 1 about")).toHaveCount(4);
  expect(Math.abs((await page.evaluate(() => scrollY)) - before)).toBeLessThan(5);
  expect(await scroller(page).evaluate((el) => el.scrollTop)).toBeGreaterThan(0);
});

test("a long answer keeps its start in view", async ({ page }) => {
  await mock(page, LONG);
  await page.goto("/");
  await ask(page, "the long one?");
  await expect(page.getByText("Sentence 1 about")).toBeVisible();
  // Smooth scroll: wait until the question bubble has settled inside the box.
  await expect
    .poll(async () => {
      const box = await scroller(page).boundingBox();
      const q = await page.getByText("the long one?").last().boundingBox();
      return q!.y >= box!.y - 1 && q!.y < box!.y + box!.height;
    })
    .toBe(true);
});

test("Arabic text gets its own direction", async ({ page }) => {
  await mock(page, "محمد مهندس منتجات في ماجرة.");
  await page.goto("/");
  await ask(page, "ما هي ماجرة؟");
  const answer = page.getByText("محمد مهندس منتجات في ماجرة.");
  await expect(answer).toHaveAttribute("dir", "auto");
  expect(await answer.evaluate((el) => getComputedStyle(el).direction)).toBe("rtl");
});

test("an Arabic question stays on the question side of an English page", async ({ page }) => {
  await mock(page, "محمد مهندس منتجات في ماجرة.");
  await page.goto("/");
  await ask(page, "ما هي ماجرة؟");
  const q = await page.getByText("ما هي ماجرة؟").last().boundingBox();
  const a = await page.getByText("محمد مهندس منتجات في ماجرة.").boundingBox();
  expect(q!.x + q!.width / 2).toBeGreaterThan(a!.x + a!.width / 2);
});

test("a source chip still jumps to its record", async ({ page }) => {
  await mock(page, "It is a booking platform.", [
    { record_id: "proj-keyraa", title: "Keyraa" },
  ]);
  await page.goto("/");
  await ask(page, "What is Keyraa?");
  await page.getByRole("button", { name: /Keyraa/ }).click();
  await expect(page.locator("#record-proj-keyraa")).toBeFocused();
});
