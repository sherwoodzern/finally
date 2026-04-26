'use client';

/**
 * Trade bar form: ticker + quantity + Buy/Sell. Market orders, instant fill.
 * Inline <p role="alert"> below buttons on 400 responses; implicit success (D-08).
 * Decision refs: D-05 (ticker regex), D-06 (quantity input), D-07 (error map),
 * D-08 (implicit success); 07-UI-SPEC §5.5; 07-RESEARCH §4 + §Code Examples.
 */

import { useRef, useState, type FormEvent } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { postTrade, TradeError } from '@/lib/api/portfolio';
import { usePriceStore } from '@/lib/price-store';

const TICKER_RE = /^[A-Z][A-Z0-9.]{0,9}$/;

const ERROR_TEXT: Record<string, string> = {
  insufficient_cash: 'Not enough cash for that order.',
  insufficient_shares: "You don't have that many shares to sell.",
  unknown_ticker: 'No such ticker.',
  price_unavailable: 'Price unavailable right now — try again.',
};
const DEFAULT_ERROR = 'Something went wrong. Try again.';

function errorMessage(code: string | null): string | null {
  if (!code) return null;
  return ERROR_TEXT[code] ?? DEFAULT_ERROR;
}

export function TradeBar() {
  const [ticker, setTicker] = useState('');
  const [quantity, setQuantity] = useState('');
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [pendingSide, setPendingSide] = useState<'buy' | 'sell' | null>(null);
  const tickerRef = useRef<HTMLInputElement>(null);
  const qc = useQueryClient();

  const mutation = useMutation({
    mutationFn: postTrade,
    onSuccess: async (res) => {
      usePriceStore.getState().flashTrade(res.ticker, 'up');
      await qc.invalidateQueries({ queryKey: ['portfolio'] });
      setTicker('');
      setQuantity('');
      setErrorCode(null);
      setPendingSide(null);
      tickerRef.current?.focus();
    },
    onError: (err: unknown) => {
      setErrorCode(err instanceof TradeError ? err.code : 'unknown');
      setPendingSide(null);
    },
  });

  function submit(side: 'buy' | 'sell') {
    return (e: FormEvent<HTMLButtonElement>) => {
      e.preventDefault();
      if (!TICKER_RE.test(ticker)) {
        setErrorCode('unknown_ticker');
        return;
      }
      const q = parseFloat(quantity);
      if (!(q > 0)) return;
      setPendingSide(side);
      setErrorCode(null);
      mutation.mutate({ ticker, side, quantity: q });
    };
  }

  const isSubmitting = mutation.isPending || pendingSide !== null;
  const errText = errorMessage(errorCode);

  return (
    <section className="bg-surface-alt border border-border-muted rounded p-4">
      <form className="flex flex-col gap-3">
        <label className="flex flex-col gap-1 text-sm text-foreground-muted">
          Ticker
          <input
            ref={tickerRef}
            type="text"
            inputMode="text"
            placeholder="AAPL"
            maxLength={10}
            value={ticker}
            onChange={(e) => {
              setTicker(e.target.value.trim().toUpperCase());
              setErrorCode(null);
            }}
            className="h-10 px-3 bg-surface border border-border-muted rounded text-foreground font-mono focus-visible:outline-2 focus-visible:outline-accent-blue"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm text-foreground-muted">
          Quantity
          <input
            type="number"
            min="0.01"
            step="0.01"
            placeholder="1"
            value={quantity}
            onChange={(e) => {
              setQuantity(e.target.value);
              setErrorCode(null);
            }}
            className="h-10 px-3 bg-surface border border-border-muted rounded text-foreground font-mono focus-visible:outline-2 focus-visible:outline-accent-blue"
          />
        </label>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={submit('buy')}
            disabled={isSubmitting}
            className="flex-1 h-10 bg-accent-purple text-white font-semibold rounded hover:brightness-110 disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-2 focus-visible:outline-accent-blue"
          >
            Buy
          </button>
          <button
            type="button"
            onClick={submit('sell')}
            disabled={isSubmitting}
            className="flex-1 h-10 bg-accent-purple text-white font-semibold rounded hover:brightness-110 disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-2 focus-visible:outline-accent-blue"
          >
            Sell
          </button>
        </div>
        {errText && (
          <p role="alert" className="text-sm text-down">
            {errText}
          </p>
        )}
      </form>
    </section>
  );
}
