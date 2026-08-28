import type { Metadata } from 'next';
import Link from 'next/link';
import './globals.css';

export const metadata: Metadata = {
  title: 'Noesis Praxis CareerOps',
  description: 'Private job-application dashboard with approval-gated workflows.',
};

const nav = [
  { href: '/', label: 'Command Center' },
  { href: '/jobs', label: 'Job Pipeline' },
  { href: '/profile', label: 'Profile & Evidence' },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="mx-auto flex min-h-screen max-w-7xl gap-6 px-4 py-4 lg:px-8">
          <aside className="hidden w-64 shrink-0 rounded-3xl border border-white/10 bg-white/5 p-5 shadow-glow lg:block">
            <div className="space-y-2">
              <div className="text-xs uppercase tracking-[0.3em] text-sky-300/80">Noesis Praxis</div>
              <div className="text-2xl font-semibold">CareerOps</div>
              <p className="text-sm text-slate-300">
                Private, approval-gated job pipeline with Hermes as supervisor and Praxis as bounded execution.
              </p>
            </div>
            <nav className="mt-8 space-y-2">
              {nav.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="block rounded-2xl border border-white/8 bg-slate-950/40 px-4 py-3 text-sm text-slate-200 transition hover:border-sky-400/40 hover:bg-slate-900/60"
                >
                  {item.label}
                </Link>
              ))}
            </nav>
            <div className="mt-8 rounded-2xl border border-sky-400/20 bg-sky-400/10 p-4 text-xs text-sky-100">
              Discovery and drafting may automate. Outreach, uploads, and submission stay behind explicit approval.
            </div>
          </aside>
          <main className="flex-1 space-y-6 pb-10">{children}</main>
        </div>
      </body>
    </html>
  );
}
