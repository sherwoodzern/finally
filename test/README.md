# FinAlly E2E Harness

Phase 10 brings up the production `finally` image alongside a Playwright runner via docker compose, then runs the seven `planning/PLAN.md` §12 demo scenarios against it in Chromium, Firefox, and WebKit. The single canonical command, run from the repo root, is:

`docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from playwright`

The compose process exits with Playwright's exit code. After a run, the inspectable HTML report is at `test/playwright-report/index.html` and per-test traces, screenshots, and videos for failures are at `test/test-results/`. To debug a single spec on a single browser locally, run:

`docker compose -f test/docker-compose.test.yml run --rm playwright npx playwright test 01-fresh-start.spec.ts --project=chromium`
