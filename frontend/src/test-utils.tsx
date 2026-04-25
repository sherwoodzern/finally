/**
 * Shared test helpers for Phase 07 component tests.
 * Wraps a component tree in a fresh QueryClient so tests don't share cache.
 */

import { type ReactElement } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, type RenderResult } from '@testing-library/react';

/** Wrap `ui` in a fresh QueryClient (retry disabled). */
export function renderWithQuery(ui: ReactElement): RenderResult {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}
