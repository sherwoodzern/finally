'use client';

/**
 * Root client provider: TanStack Query client + SSE EventSource owner.
 * Mounted once from layout.tsx. StrictMode-safe via useState-init singleton.
 * Decision refs: 07-RESEARCH §2 Pattern 5.
 */

import { useState, type ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PriceStreamProvider } from '@/lib/price-stream-provider';

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 10_000,
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      <PriceStreamProvider>{children}</PriceStreamProvider>
    </QueryClientProvider>
  );
}
