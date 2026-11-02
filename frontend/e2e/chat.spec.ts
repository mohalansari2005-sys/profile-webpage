import { expect, test, type Page } from "@playwright/test";
import { en } from "../messages/en";

const CHAT_API = "http://chat.test/api/chat/";

const LONG = Array.from({ length: 40 }, (_, i) => `Sentence ${i + 1} about the work.`).join(" ");

function mock(page: Page, answer: string, sources: { record_id: string; title: string }[] = []) {
  return page.route(CHAT_API, (route) =>
    route.fulfill({ json: { answer, sources, refused: false } }),
  );
}

async function ask(page: Page, question: string) {
  await page.locator("#ask-input").fill(question);
  await page.getByRole("button", { name: "Send question" }).click();
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

test("an answer keeps its line breaks", async ({ page }) => {
  await mock(page, "\nFirst paragraph.\n\nA list:\n- one\n- two\n");
  await page.goto("/");
  await ask(page, "Two parts?");
  const answer = page.getByText("First paragraph.");
  // Under a busy parallel run the default 5s can pass before the fetch resolves.
  await expect(answer).toBeVisible({ timeout: 15_000 });
  // Rendered text: collapsed whitespace would read back as one line, and the
  // stray newlines at either end are trimmed.
  expect(await answer.evaluate((el: HTMLElement) => el.innerText)).toBe(
    "First paragraph.\n\nA list:\n- one\n- two",
  );
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
  // A reader typing has the input on screen. Bring it there first, or
  // Playwright's own scroll-to-click would be counted as the page moving.
  await page.locator("#ask-input").scrollIntoViewIfNeeded();
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

test("a short answer after a long one is still brought into view", async ({ page }) => {
  await page.route(CHAT_API, (route) => {
    const question = JSON.parse(route.request().postData()!).question as string;
    return route.fulfill({
      json: { answer: question.includes("long") ? LONG : "Short reply.", sources: [], refused: false },
    });
  });
  await page.goto("/");
  await ask(page, "the long one?");
  await expect(page.getByText("Sentence 1 about")).toBeVisible();
  await ask(page, "and a short one?");
  const reply = page.getByText("Short reply.");
  await expect(reply).toBeVisible();
  await expect
    .poll(async () => {
      const box = await scroller(page).boundingBox();
      const r = await reply.boundingBox();
      return r!.y >= box!.y && r!.y + r!.height <= box!.y + box!.height + 1;
    })
    .toBe(true);
});

test("Arabic text gets its own direction", async ({ page }) => {
  await mock(page, "محمد يشتغل مهندس منتجات في مجرة.");
  await page.goto("/");
  await ask(page, "وش هي مجرة؟");
  const answer = page.getByText("محمد يشتغل مهندس منتجات في مجرة.");
  // Wait for the mocked reply to render first; under a busy parallel run the
  // default 5s can pass before the fetch resolves.
  await expect(answer).toBeVisible({ timeout: 15_000 });
  await expect(answer).toHaveAttribute("dir", "auto");
  expect(await answer.evaluate((el) => getComputedStyle(el).direction)).toBe("rtl");
});

test("an Arabic question stays on the question side of an English page", async ({ page }) => {
  await mock(page, "محمد يشتغل مهندس منتجات في مجرة.");
  await page.goto("/");
  await ask(page, "وش هي مجرة؟");
  const answer = page.getByText("محمد يشتغل مهندس منتجات في مجرة.");
  await expect(answer).toBeVisible();
  const q = await page.getByText("وش هي مجرة؟").last().boundingBox();
  const a = await answer.boundingBox();
  expect(q!.x + q!.width / 2).toBeGreaterThan(a!.x + a!.width / 2);
});

// Exactly what the backend sends: DRF's own 429 body. The daily cap has no
// wait to report (GlobalDailyThrottle.wait() is None); the per-visitor limit
// always has one.
const DAILY_CAP_BODY = { detail: "Request was throttled." };
const PER_VISITOR_BODY = { detail: "Request was throttled. Expected available in 42 seconds." };

test("the daily cap says tomorrow and offers no retry", async ({ page }) => {
  await page.route(CHAT_API, (route) => route.fulfill({ status: 429, json: DAILY_CAP_BODY }));
  await page.goto("/");
  await ask(page, "Anything?");
  await expect(page.getByText(en.ask.errors.dailyCap)).toBeVisible();
  await expect(page.getByRole("button", { name: en.ask.tryAgain })).toHaveCount(0);
  // Nothing to retry, so focus goes back to the input rather than <body>.
  await expect(page.locator("#ask-input")).toBeFocused();
});

test("the backend's explicit daily_cap code is read before DRF's wording", async ({ page }) => {
  await page.route(CHAT_API, (route) => route.fulfill({ status: 429, json: {
    detail: "Request was throttled. Expected available in 42 seconds.", code: "daily_cap" } }));
  await page.goto("/");
  await ask(page, "Anything?");
  await expect(page.getByText(en.ask.errors.dailyCap)).toBeVisible();
});

test("after an error, focus lands on Try again, and again when the retry fails", async ({ page }) => {
  await page.route(CHAT_API, (route) => route.fulfill({ status: 500, body: "boom" }));
  await page.goto("/");
  // A reader typing has the input on screen; focus only moves to a chat the
  // reader is still at. (Playwright's own focus would start a smooth scroll
  // that the instant error beats.)
  await page.locator("#ask-input").scrollIntoViewIfNeeded();
  await page.locator("#ask-input").fill("question");
  await page.locator("#ask-input").press("Enter");
  const retry = page.getByRole("button", { name: en.ask.tryAgain });
  await expect(retry).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.getByText(en.ask.errors.server)).toBeVisible();
  await expect(retry).toBeFocused();
});

// Answers take seconds; a reader may scroll off to read, or move focus to
// something else, while one is on its way.
function delayedAnswer(page: Page, answer: string) {
  return page.route(CHAT_API, async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 1_000));
    await route.fulfill({ json: { answer, sources: [], refused: false } });
  });
}

// The reader scrolled off with the mouse while waiting, so focus sits on
// <body> and Space is how they page down. Focusing the off-screen chat there,
// even without scrolling, turned that Space into a typed space (and a jump
// back to the input) or a click on Try again.
async function expectSpaceToPageDown(page: Page) {
  // The refocus runs in an effect after the reply renders; give it the chance
  // to run before reading where the keyboard is.
  await page.waitForTimeout(300);
  await expect(page.locator("#ask *:focus")).toHaveCount(0);
  await page.keyboard.press("Space");
  await expect.poll(() => page.evaluate(() => scrollY)).toBeGreaterThan(100);
  // Paged down, not pulled ~3000px back to the chat.
  const input = await page.locator("#ask-input").boundingBox();
  expect(input!.y).toBeGreaterThan(page.viewportSize()!.height);
}

test("an answer arriving after the reader scrolled away leaves the page to them", async ({ page }) => {
  await delayedAnswer(page, "A late answer.");
  await page.goto("/");
  await ask(page, "Take your time?");
  await page.evaluate(() => scrollTo({ top: 0, behavior: "instant" }));
  await expect(page.getByText("A late answer.")).toBeVisible();
  await expectSpaceToPageDown(page);
  await expect(page.locator("#ask-input")).toHaveValue("");
});

test("a failure after the reader scrolled away does not arm Space as a retry", async ({ page }) => {
  let requests = 0;
  await page.route(CHAT_API, async (route) => {
    requests++;
    await new Promise((resolve) => setTimeout(resolve, 1_000));
    await route.fulfill({ status: 500, body: "boom" });
  });
  await page.goto("/");
  await ask(page, "Take your time?");
  await page.evaluate(() => scrollTo({ top: 0, behavior: "instant" }));
  await expect(page.getByText(en.ask.errors.server)).toBeVisible();
  await expectSpaceToPageDown(page);
  // Every retry counts against the visitor's and the day's limits.
  expect(requests).toBe(1);
});

test("an answer does not take focus from what the reader moved to", async ({ page }) => {
  await delayedAnswer(page, "A late answer.");
  await page.goto("/");
  await ask(page, "Take your time?");
  const link = page.getByRole("link", { name: "Keyraa on GitHub" });
  await link.evaluate((el: HTMLElement) => el.focus({ preventScroll: true }));
  await expect(page.getByText("A late answer.")).toBeVisible();
  await expect(link).toBeFocused();
});

test("a long answer offers a named button back to the latest message", async ({ page }) => {
  await mock(page, LONG);
  await page.goto("/");
  await ask(page, "the long one?");
  await expect(page.getByText("Sentence 1 about")).toBeVisible();
  // A long answer is pinned at its start, so the box is no longer at the bottom.
  await expect(page.getByRole("button", { name: en.ask.scrollToLatest })).toBeVisible();
});

for (const [name, body] of [
  ["the per-visitor limit", JSON.stringify(PER_VISITOR_BODY)],
  [
    "the per-visitor limit, one second left",
    JSON.stringify({ detail: "Request was throttled. Expected available in 1 second." }),
  ],
  ["an unreadable body", "<html>Too Many Requests</html>"],
  ["a body with no detail", "{}"],
] as const) {
  test(`any other 429 (${name}) is the one-minute limit`, async ({ page }) => {
    await page.route(CHAT_API, (route) => route.fulfill({ status: 429, body }));
    await page.goto("/");
    await ask(page, "Anything?");
    await expect(page.getByText(en.ask.errors.throttled)).toBeVisible();
    await expect(page.getByRole("button", { name: en.ask.tryAgain })).toBeVisible();
  });
}

test("a source chip still jumps to its record", async ({ page }) => {
  await mock(page, "It is a booking platform.", [
    { record_id: "proj-keyraa", title: "Keyraa" },
  ]);
  await page.goto("/");
  await ask(page, "What is Keyraa?");
  // The chat box may still be smooth-scrolling to the new answer when the chip
  // first becomes clickable; under a busy parallel run a click can land on the
  // moving box instead. Retry click + focus together rather than assume the
  // first click hit (it passes 60/60 when the machine is not saturated).
  const card = page.locator("#record-proj-keyraa");
  await expect(async () => {
    await page.getByRole("button", { name: /Keyraa/ }).click();
    await expect(card).toBeFocused({ timeout: 1500 });
  }).toPass({ timeout: 15_000 });
});

test.describe("on a short phone", () => {
  test.use({ viewport: { width: 375, height: 667 }, hasTouch: true, isMobile: true });

  test("a source chip lands the record's title below the sticky tool strip", async ({ page }) => {
    await mock(page, "It is a booking platform.", [
      { record_id: "proj-keyraa", title: "Keyraa" },
    ]);
    await page.goto("/");
    await ask(page, "What is Keyraa?");
    const card = page.locator("#record-proj-keyraa");
    // Retry click + focus together (see "a source chip still jumps").
    await expect(async () => {
      await page.getByRole("button", { name: /Keyraa/ }).click();
      await expect(card).toBeFocused({ timeout: 1500 });
    }).toPass({ timeout: 15_000 });
    // The card is taller than this screen; centring it hid the title.
    const strip = page.locator("#work > div").first();
    await expect
      .poll(async () => {
        const [s, title] = [await strip.boundingBox(), await card.locator("h3").boundingBox()];
        return title!.y >= s!.y + s!.height && title!.y + title!.height <= 667;
      })
      .toBe(true);
  });

  test("a long URL wraps inside its bubble instead of being cut off", async ({ page }) => {
    const url = "https://github.com/mohalansari2005-sys/keyraa-hotel-booking";
    await mock(page, `The code is at ${url}`);
    await page.goto("/");
    await ask(page, `Is it ${url}?`);
    await expect(page.getByText(`The code is at ${url}`)).toBeVisible();
    for (const text of [`Is it ${url}?`, `The code is at ${url}`]) {
      const bubble = page.getByText(text).last().locator("..");
      const { scroll, client } = await bubble.evaluate((el) => ({
        scroll: el.scrollWidth,
        client: el.clientWidth,
      }));
      expect(scroll, text).toBeLessThanOrEqual(client);
    }
  });
});
