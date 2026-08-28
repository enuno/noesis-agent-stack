import { cn } from '@/lib/utils';
import type { ReactNode } from 'react';

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return <section className={cn('rounded-3xl border border-white/10 bg-white/5 p-5 shadow-glow', className)}>{children}</section>;
}

export function CardTitle({ children }: { children: ReactNode }) {
  return <h2 className="text-lg font-semibold tracking-tight">{children}</h2>;
}

export function CardSubtitle({ children }: { children: ReactNode }) {
  return <p className="mt-1 text-sm text-slate-300">{children}</p>;
}

export function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'success' | 'warning' | 'danger' | 'info' }) {
  const tones = {
    neutral: 'border-white/10 bg-white/8 text-slate-200',
    success: 'border-emerald-400/20 bg-emerald-400/10 text-emerald-200',
    warning: 'border-amber-400/20 bg-amber-400/10 text-amber-200',
    danger: 'border-rose-400/20 bg-rose-400/10 text-rose-200',
    info: 'border-sky-400/20 bg-sky-400/10 text-sky-200',
  } as const;
  return <span className={cn('inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium', tones[tone])}>{children}</span>;
}

export function Button({ children, variant = 'primary', type = 'button', className, disabled = false }: { children: ReactNode; variant?: 'primary' | 'secondary' | 'ghost'; type?: 'button' | 'submit' | 'reset'; className?: string; disabled?: boolean }) {
  const styles = {
    primary: 'bg-sky-500 text-slate-950 hover:bg-sky-400',
    secondary: 'border border-white/10 bg-white/5 text-slate-100 hover:bg-white/10',
    ghost: 'text-slate-200 hover:bg-white/5',
  } as const;
  return (
    <button type={type} disabled={disabled} className={cn('rounded-2xl px-4 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-60', styles[variant], className)}>
      {children}
    </button>
  );
}

export function StatCard({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <Card className="p-4">
      <div className="text-xs uppercase tracking-[0.22em] text-slate-400">{label}</div>
      <div className="mt-2 text-3xl font-semibold">{value}</div>
      {hint ? <div className="mt-1 text-sm text-slate-400">{hint}</div> : null}
    </Card>
  );
}

export function ProgressBar({ value }: { value: number }) {
  return (
    <div className="h-2 overflow-hidden rounded-full bg-white/10">
      <div className="h-full rounded-full bg-gradient-to-r from-sky-400 to-fuchsia-400" style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </div>
  );
}
