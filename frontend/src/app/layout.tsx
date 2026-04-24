import type { Metadata } from 'next';
import './globals.css';
import { PriceStreamProvider } from '@/lib/price-stream-provider';

export const metadata: Metadata = {
  title: 'FinAlly',
  description: 'AI trading workstation',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-surface text-foreground">
        <PriceStreamProvider>{children}</PriceStreamProvider>
      </body>
    </html>
  );
}
