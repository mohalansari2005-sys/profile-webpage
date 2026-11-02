import { expect, test, VISIT_API, type Page } from "./fixtures";
import { en } from "../messages/en";

// The beacon's URL is derived from the chat URL baked in at build time (see
// CI), and every request to it is answered here, so these tests never touch a
// real backend.

type Visit = { path: string; referrer: string; source: string };

/** Records each beacon and answers it the way the backend does: an empty 204. */
async function recordVisits(page: Page) {
  const visits: Visit[] = [];
  const contentTypes: string[] = [];
  await page.route(VISIT_API, (route) => {
    visits.push(JSON.parse(route.request().postData() ?? "{}"));
    contentTypes.push(route.request().headers()["content-type"] ?? "");
    return route.fulfill({ status: 204 });
  });
  return { visits, contentTypes };
}

// Absence cannot be polled for: give a stray second beacon time to arrive.
const QUIET_MS = 1000;

test("a visit to / is counted once, with its path", async ({ page }) => {
  const { visits, contentTypes } = await recordVisits(page);
  await page.goto("/");
  await expect.poll(() => visits.length).toBe(1);
  expect(visits[0]).toEqual({ path: "/", referrer: "", source: "" });
  // text/plain is what lets the beacon go cross-origin without a preflight.
  expect(contentTypes[0]).toMatch(/^text\/plain/);
  await page.waitForTimeout(QUIET_MS);
  expect(visits).toHaveLength(1);
});

test("a visit to /ar is counted once, with its path", async ({ page }) => {
  const { visits } = await recordVisits(page);
  await page.goto("/ar");
  await expect.poll(() => visits.length).toBe(1);
  expect(visits[0].path).toBe("/ar");
  await page.waitForTimeout(QUIET_MS);
  expect(visits).toHaveLength(1);
});

test("the campaign source rides along", async ({ page }) => {
  const { visits } = await recordVisits(page);
  await page.goto("/?utm_source=linkedin");
  await expect.poll(() => visits.length).toBe(1);
  await page.goto("/ar?ref=cv");
  await expect.poll(() => visits.length).toBe(2);
  expect(visits.map((v) => [v.path, v.source])).toEqual([
    ["/", "linkedin"],
    ["/ar", "cv"],
  ]);
});

test("the language toggle sends the page it came from as the referrer", async ({ page }) => {
  const { visits } = await recordVisits(page);
  await page.goto("/");
  await expect.poll(() => visits.length).toBe(1);
  await page.getByRole("link", { name: en.lang.switchAria }).click();
  await expect.poll(() => visits.length).toBe(2);
  // The backend blanks its own host; the browser just reports it.
  expect(new URL(visits[1].referrer).pathname).toBe("/");
  expect(visits[1].path).toBe("/ar");
});

test("?analytics=off stops this browser counting, ?analytics=on resumes it", async ({ page }) => {
  const { visits } = await recordVisits(page);

  await page.goto("/?analytics=off");
  // The flag is written by the same effect that would send the beacon, so
  // once it is there the beacon has had its chance.
  await expect
    .poll(() => page.evaluate(() => localStorage.getItem("analytics")))
    .toBe("off");
  // ...and the switch leaves the address bar, so a copy of this link cannot
  // opt out whoever opens it.
  await expect(page).toHaveURL((url) => url.pathname === "/" && url.search === "");
  await page.goto("/");
  await page.goto("/ar");
  await page.waitForTimeout(QUIET_MS);
  expect(visits).toHaveLength(0);

  await page.goto("/ar?ref=cv&analytics=on#work");
  await expect.poll(() => visits.length).toBe(1);
  expect(await page.evaluate(() => localStorage.getItem("analytics"))).toBeNull();
  // Only the switch goes; the other parameters and the hash stay.
  await expect(page).toHaveURL((url) => url.search === "?ref=cv" && url.hash === "#work");
  await page.goto("/ar");
  await expect.poll(() => visits.length).toBe(2);
  expect(visits.map((v) => [v.path, v.source])).toEqual([["/ar", "cv"], ["/ar", ""]]);
});

// A reader who chose Arabic is sent from / to /ar by a script in <head>
// (site-head.tsx). That redirect used to drop the query.
test.describe("a returning Arabic reader who opens /", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/ar");
    await expect.poll(() => page.evaluate(() => localStorage.getItem("lang"))).toBe("ar");
  });

  test("keeps the campaign source", async ({ page }) => {
    const { visits } = await recordVisits(page);
    await page.goto("/?utm_source=linkedin");
    await expect.poll(() => visits.length).toBe(1);
    expect(visits[0]).toMatchObject({ path: "/ar", source: "linkedin" });
    await page.waitForTimeout(QUIET_MS);
    expect(visits).toHaveLength(1);
  });

  test("can still switch analytics off", async ({ page }) => {
    const { visits } = await recordVisits(page);
    await page.goto("/?analytics=off");
    await expect
      .poll(() => page.evaluate(() => localStorage.getItem("analytics")))
      .toBe("off");
    await expect(page).toHaveURL((url) => /^\/ar\/?$/.test(url.pathname) && url.search === "");
    await page.waitForTimeout(QUIET_MS);
    expect(visits).toHaveLength(0);
  });
});
