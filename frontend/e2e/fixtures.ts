import { test as base } from "@playwright/test";

// Specs import from here instead of "@playwright/test": same API, plus the
// one thing every test needs now.
export * from "@playwright/test";

/** Where the page-view beacon goes (lib/visit.ts, from the build's chat URL). */
export const VISIT_API = "http://chat.test/api/visit/";

export const test = base.extend<{ answerVisits: void }>({
  // Every page load sends a beacon. Unanswered, each one is a DNS lookup for
  // chat.test and a console error in a test that is not about analytics, so
  // the test's context answers it the way the backend does. A spec that checks
  // the beacon routes it on the page, which takes precedence over this. A
  // context a test opens itself (browser.newContext) is not covered: route
  // VISIT_API there too, as responsive.spec.ts does.
  answerVisits: [
    async ({ context }, use) => {
      await context.route(VISIT_API, (route) => route.fulfill({ status: 204 }));
      await use();
    },
    { auto: true },
  ],
});
