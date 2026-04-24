---
phase: 06
slug: frontend-scaffold-sse
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-23
---

# Phase 06 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest 4.1.5 + @testing-library/react 16.3.2 + jsdom 29.0.2 |
| **Config file** | `frontend/vitest.config.mts` (none today — Wave 0 installs) |
| **Setup file** | `frontend/vitest.setup.ts` (none today — Wave 0 installs) |
| **Quick run command** | `cd frontend && npm test -- --run src/lib/price-stream.test.ts` |
| **Full suite command** | `cd frontend && npm run test:ci` |
| **Build gate** | `cd frontend && npm run build` (exit 0 + `frontend/out/` populated) |
| **Type check** | transitively via `next build` (`tsc --noEmit`) |
| **Lint** | `cd frontend && npm run lint` |
| **Estimated runtime** | ~3 s unit tests; ~30 s build+lint+tests combined |

---

## Sampling Rate (Nyquist threshold)

**The Nyquist threshold for Phase 06 frontend-store correctness is "one ingest per event, assertion after each event."** The backend emits at ~500 ms cadence via `backend/app/market/stream.py`. The store MUST record every distinct emission, not an aggregate — a single end-of-test assertion would permit regressions where intermediate ticks are lost.

- **After every task commit:** Run the quick run command on the changed test file. Turnaround < 3 s.
- **After every plan wave:** Run the full suite command + `npm run build` + `npm run lint`. Turnaround < 30 s. Green required.
- **Before `/gsd-verify-work`:** Full suite green AND manual `/debug` page verified against a running backend (≥10 tickers with live-updating prices, direction flags flipping, `session_start_price` stable across multiple ticks, connection status reading `connected`).
- **Max feedback latency:** 3 s per task, 30 s per wave.

---

## Per-Task Verification Map

> Plan files not yet authored. The planner populates one row per task after `/gsd-plan-phase` completes. Each task must map to at least one of the requirements below or be explicitly flagged as "scaffold/setup" (Wave 0).

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| _(populated by planner)_ | — | — | FE-01 / FE-02 | — | — | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Requirement → Test Coverage

| Req ID | Behavior | Test Type | Automated Command |
|--------|----------|-----------|-------------------|
| FE-01 | `frontend/` scaffolded with TS + Tailwind + App Router + `output: 'export'` | build | `cd frontend && npm run build` (exit 0 + `test -d frontend/out`) |
| FE-01 | Dark theme tokens + accent colors resolve in compiled CSS | build | grep `frontend/out/_next/static/css/*.css` for `#ecad0a`, `#209dd7`, `#753991` |
| FE-02 | Single `EventSource` connects idempotently (StrictMode-safe) | unit | `-t 'connect is idempotent'` |
| FE-02 | First event sets `session_start_price` per ticker (frozen thereafter) | unit | `-t 'first event sets session_start_price'` |
| FE-02 | Subsequent events update `price`, `previous_price`, `change`, `direction` without overwriting `session_start_price` | unit | `-t 'subsequent events update price'` |
| FE-02 | `onopen` → `connected`; `onerror` CONNECTING → `reconnecting`; CLOSED → `disconnected` | unit | `-t 'status state machine'` (3 cases) |
| FE-02 | Malformed payloads are logged and dropped; valid entries in the same batch still ingest | unit | `-t 'malformed payload'` |
| FE-02 | Selector-based subscribe re-renders only when the subscribed ticker changes | unit | `-t 'selector re-render'` |

---

## Wave 0 Requirements

- [ ] `frontend/` scaffold (`create-next-app` with TS + Tailwind + App Router + src dir)
- [ ] `frontend/package.json` engines pin (`node >=20.0.0 <21`), `test` + `test:ci` scripts
- [ ] `frontend/vitest.config.mts` (jsdom env, `@vitejs/plugin-react`, setup file registered)
- [ ] `frontend/vitest.setup.ts` (imports `@testing-library/jest-dom/vitest`)
- [ ] Dev deps installed: `vitest`, `@vitest/coverage-v8`, `@vitejs/plugin-react`, `jsdom`, `@testing-library/react`, `@testing-library/jest-dom`, `vite-tsconfig-paths`
- [ ] Prod dep installed: `zustand`
- [ ] `frontend/src/lib/sse-types.ts` (`Tick`, `RawPayload`, `ConnectionStatus`, `Direction`)
- [ ] `frontend/src/lib/price-store.ts` (Zustand + `__setEventSource` DI hook for tests)
- [ ] `frontend/src/lib/price-stream-provider.tsx` (owns `EventSource` lifecycle)
- [ ] `frontend/src/lib/price-stream.test.ts` (MockEventSource + 8 unit tests above)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `/debug` page renders live store contents against a running backend | FE-02 (wire integration) | Real browser + real backend proves JSON shape alignment, dev-proxy semantics, browser auto-reconnect — impossible to automate without Playwright (Phase 10) | 1) `cd backend && uv run uvicorn app.main:app --port 8000` in terminal A. 2) `cd frontend && npm run dev` in terminal B. 3) Open `http://localhost:3000/debug` and confirm ≥10 tickers with live-updating prices, direction flags flipping, `session_start_price` stable across ≥5 ticks, status reading `connected`. |
| Dark theme visual inspection | FE-01 | CSS variable resolution at runtime requires a real browser; build-time grep only verifies values are in the stylesheet | Open `http://localhost:3000/` and confirm `#0d1117` background + `#ecad0a` accent visible |

---

## Out of Scope for Phase 06

| Capability | Deferred To | Rationale |
|------------|-------------|-----------|
| Playwright E2E reconnect flow | Phase 10 (TEST-03, TEST-04) | Phase 6 proves reconnect via Vitest `onerror` CONNECTING/CLOSED cases (D-22) |
| FastAPI `StaticFiles` mount of the export | Phase 8 (APP-02) | Phase 6 only builds; mount is Phase 8's job |
| Frontend trading/panel component tests | Phase 8 (TEST-02) | Phase 6 covers only the SSE store; panels ship in Phase 7 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or a Wave 0 dependency
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references above
- [ ] No watch-mode flags anywhere (`--run` is the default; `--watch` is banned in CI)
- [ ] Feedback latency < 30 s per wave
- [ ] `nyquist_compliant: true` set in frontmatter after planner populates task map

**Approval:** pending — planner fills per-task rows, then sign off.
