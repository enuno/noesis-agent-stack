import { LoginForm } from './login-form';

export default function LoginPage({ searchParams }: { searchParams?: { next?: string } }) {
  const next = searchParams?.next ?? '/';
  return (
    <div className="mx-auto flex min-h-screen max-w-md items-center px-4 py-16">
      <div className="w-full rounded-3xl border border-white/10 bg-white/5 p-6 shadow-glow">
        <div className="text-xs uppercase tracking-[0.3em] text-sky-300/80">Noesis Praxis</div>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">CareerOps login</h1>
        <p className="mt-2 text-sm text-slate-300">Sign in with your Supabase-backed workspace account to access the private job pipeline.</p>
        <div className="mt-6">
          <LoginForm nextPath={next} />
        </div>
      </div>
    </div>
  );
}
