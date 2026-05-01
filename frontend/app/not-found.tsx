export default function NotFoundPage() {
  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <div className="showcase-shell w-full max-w-xl rounded-[32px] border border-slate-200/90 px-8 py-10 text-center">
        <div className="section-kicker">Page Not Found</div>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">
          This route does not exist in GitHub AI Trend Analyzer.
        </h1>
        <p className="mt-4 text-sm leading-7 text-slate-600">
          Return to the dashboard to continue tracking repository momentum, topic
          rotation, and AI-generated market intelligence.
        </p>
        <a
          href="/"
          className="mt-6 inline-flex rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
        >
          Back to dashboard
        </a>
      </div>
    </main>
  );
}
