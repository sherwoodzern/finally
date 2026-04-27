// test/07-sse-reconnect.spec.ts
// PLAN.md §12 row 7 — SSE resilience: disconnect and verify reconnection.
//
// Pattern: arm context.route() with route.abort('connectionreset'), reload
// to force EventSource re-creation, observe the connection-status state
// machine walk to reconnecting/disconnected, then unroute and observe the
// dot return to connected.
//
// Decision refs: RESEARCH.md §"SSE Reconnect Test Pattern" lines 731-768
// (canonical pattern, key API notes, WebKit caveat); §"Pitfall 3" lines
// 926-934 (issue #15353 affects fulfilling not aborting); §"Pitfall 7"
// lines 966-974 (WebKit first-paint lateness — use 15-20s timeouts).
// PATTERNS.md lines 358-371 (invariants).

import { test, expect } from '@playwright/test';

test('SSE reconnect: dot flips to reconnecting/disconnected on abort, returns to connected on unroute', async ({
  page,
  context,
}) => {
  // 1. Confirm initial connected state. The 10s timeout absorbs cold-start
  //    (compose start_period: 15s healthcheck plus the simulator's first tick).
  //    Use toBeAttached (not toBeVisible) because ConnectionDot is a 10x10px
  //    span with no text content — Playwright's visibility heuristics flag
  //    colored-only nodes as hidden on WebKit (and intermittently elsewhere).
  //    The aria-label match is what proves the state machine; DOM attachment
  //    is sufficient (Rule 1 deviation from RESEARCH.md canonical body).
  await page.goto('/');
  await expect(page.getByLabel('SSE connected')).toBeAttached({ timeout: 10_000 });

  // 2. Arm the abort. context.route (NOT page.route) covers ALL future
  //    requests including the EventSource's auto-retries — survives
  //    page.reload() (RESEARCH.md "Key API notes" line 772).
  //    route.abort('connectionreset') simulates a TCP RST. We are NOT
  //    fulfilling SSE — Playwright issue #15353 does not apply
  //    (RESEARCH.md Pitfall 3).
  await context.route('**/api/stream/prices', (route) =>
    route.abort('connectionreset'),
  );

  // 3. Trigger a reconnect cycle. page.reload() forces the EventSource to
  //    re-create; the new connection hits the abort and the connection-status
  //    state machine walks aria-label "SSE reconnecting" or "SSE disconnected".
  //    The regex tolerates either non-connected state because the yellow phase
  //    can be too brief to catch deterministically (RESEARCH.md line 661).
  //    15s timeout is the WebKit budget per Pitfall 7.
  await page.reload();

  await expect(
    page.getByLabel(/^SSE (reconnecting|disconnected)$/),
  ).toBeAttached({ timeout: 15_000 });

  // 4. Lift the abort. Subsequent EventSource retries succeed (server
  //    retry: 1000 gives a known 1s reconnect floor). EventSource backs off
  //    exponentially after multiple failures, so the 20s timeout is the
  //    WebKit-specific budget per RESEARCH.md WebKit caveat (line 783).
  await context.unroute('**/api/stream/prices');

  await expect(page.getByLabel('SSE connected')).toBeAttached({ timeout: 20_000 });
});
