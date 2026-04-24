export default function Page() {
  return (
    <main className="min-h-screen p-6">
      <h1 className="text-2xl font-semibold text-accent-yellow">FinAlly</h1>
      <p className="mt-2 text-foreground-muted">AI Trading Workstation</p>
      <p className="mt-4 text-sm text-foreground-muted">
        Dev note: see{' '}
        <a
          href="/debug"
          className="text-accent-blue underline underline-offset-2 hover:text-accent-yellow"
        >
          /debug
        </a>
        {' '}for the live price stream.
      </p>
    </main>
  );
}
