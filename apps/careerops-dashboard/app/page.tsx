import Link from 'next/link';
import { redirect } from 'next/navigation';
import { BriefcaseBusiness, CheckCircle2, Clock3, ShieldCheck, Sparkles, TriangleAlert } from 'lucide-react';
import { Card, CardSubtitle, CardTitle, ProgressBar, StatCard, Badge, Button } from '@/components/ui';
import { formatDate, formatCurrency } from '@/lib/utils';
import { getOwnerId } from '@/lib/auth';
import { getDashboardMetrics, listApplications, listJobs, getProfile, listQueueTasks } from '@/lib/store';

export default async function HomePage() {
  const ownerId = await getOwnerId().catch(() => null);
  if (!ownerId) redirect('/login?next=/');
  const [metrics, jobs, applications, profile, queueTasks] = await Promise.all([
    getDashboardMetrics(ownerId),
    listJobs({ ownerId }),
    listApplications(ownerId),
    getProfile(ownerId),
    listQueueTasks(ownerId),
  ]);
  const pursuing = jobs.filter((job) => job.decision === 'pursue').slice(0, 3);
  const dueFollowUps = applications.filter((app) => app.follow_up_due_at).slice(0, 3);

  return (
    <div className="space-y-6">
      <header className="rounded-3xl border border-white/10 bg-gradient-to-br from-sky-500/10 to-fuchsia-500/10 p-6 shadow-glow">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-sky-400/20 bg-sky-400/10 px-3 py-1 text-xs font-medium uppercase tracking-[0.22em] text-sky-100">
              <ShieldCheck className="h-3.5 w-3.5" /> Private CareerOps control plane
            </div>
            <h1 className="text-4xl font-semibold tracking-tight">Command Center</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-300">
              Hermes schedules, scores, and gates. Praxis collects and drafts. The dashboard keeps discovery fast while outreach, uploads, and submission remain explicitly approval-gated.
            </p>
          </div>
          <div className="space-y-2 text-right text-sm text-slate-300">
            <div>Profile: {profile?.title ?? 'No profile loaded'}</div>
            <div>Comp floor: {formatCurrency(profile?.compensation_floor_usd ?? null)} base</div>
            <div>Last run: {formatDate(metrics.last_successful_run)}</div>
          </div>
        </div>
      </header>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Qualified roles" value={metrics.qualified} hint="Ready for human review" />
        <StatCard label="Awaiting approval" value={metrics.blocked_actions} hint="Approval requests in flight" />
        <StatCard label="Follow-ups due" value={dueFollowUps.length} hint="5–7 business day reminders" />
        <StatCard label="Queue depth" value={metrics.queue_depth} hint="Discovery + drafting backlog" />
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
        <Card>
          <CardTitle>Funnel</CardTitle>
          <CardSubtitle>discovered → qualified → selected → packet ready → submitted → interview → offer</CardSubtitle>
          <div className="mt-6 grid gap-5">
            {[
              ['discovered', metrics.discovered],
              ['qualified', metrics.qualified],
              ['selected', metrics.selected],
              ['packet ready', metrics.packet_ready],
              ['submitted', metrics.submitted],
              ['interview', metrics.interview],
              ['offer', metrics.offer],
            ].map(([label, value]) => (
              <div key={label as string}>
                <div className="mb-2 flex items-center justify-between text-sm text-slate-300">
                  <span className="capitalize">{label}</span>
                  <span>{value as number}</span>
                </div>
                <ProgressBar value={Math.min(100, (value as number) * 10)} />
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <CardTitle>Agent health</CardTitle>
          <CardSubtitle>last successful run, source failures, blocked actions, queue depth</CardSubtitle>
          <div className="mt-4 space-y-3 text-sm text-slate-300">
            <div className="flex items-center justify-between"><span>Last successful run</span><span>{formatDate(metrics.last_successful_run)}</span></div>
            <div className="flex items-center justify-between"><span>Source failures</span><span>{metrics.source_failures}</span></div>
            <div className="flex items-center justify-between"><span>Blocked actions</span><span>{metrics.blocked_actions}</span></div>
            <div className="flex items-center justify-between"><span>Queue depth</span><span>{metrics.queue_depth}</span></div>
          </div>
          <div className="mt-5 flex flex-wrap gap-2">
            <Badge tone="info">Hermes orchestration</Badge>
            <Badge tone="success">RLS ready</Badge>
            <Badge tone="warning">Submission gated</Badge>
          </div>
        </Card>
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardTitle>High-conviction roles</CardTitle>
          <CardSubtitle>Top pursuit targets surfaced by the scoring engine.</CardSubtitle>
          <div className="mt-4 space-y-3">
            {pursuing.map((job) => (
              <Link key={job.id} href={`/jobs/${job.id}`} className="block rounded-2xl border border-white/10 bg-black/20 p-4 transition hover:border-sky-400/40 hover:bg-black/30">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="font-medium">{job.company} · {job.title}</div>
                    <div className="mt-1 text-sm text-slate-300">{job.location ?? 'Location unknown'} · {job.remote_policy ?? 'remote policy unknown'}</div>
                  </div>
                  <div className="text-right text-sm">
                    <div className="font-semibold text-sky-200">{job.fit_score.toFixed(1)}</div>
                    <div className="text-slate-400">fit</div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </Card>

        <Card>
          <CardTitle>Follow-up queue</CardTitle>
          <CardSubtitle>Applications approaching review or follow-up deadlines.</CardSubtitle>
          <div className="mt-4 space-y-3">
            {dueFollowUps.map((application) => (
              <div key={application.id} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <div className="font-medium">Application {application.id}</div>
                    <div className="mt-1 text-sm text-slate-300">Follow up due {formatDate(application.follow_up_due_at)}</div>
                  </div>
                  <Clock3 className="h-5 w-5 text-amber-300" />
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button>Generate digest</Button>
            <Button variant="secondary">Review queue</Button>
          </div>
        </Card>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardTitle>Discovery</CardTitle>
          <CardSubtitle>Official company pages and public ATS retrieval only.</CardSubtitle>
        </Card>
        <Card>
          <CardTitle>Drafting</CardTitle>
          <CardSubtitle>Cover letters, résumé deltas, and screening answers stay reviewable.</CardSubtitle>
        </Card>
        <Card>
          <CardTitle>Control</CardTitle>
          <CardSubtitle>Outreach, uploads, and final submit require explicit approval.</CardSubtitle>
        </Card>
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardTitle>Worker queue</CardTitle>
          <CardSubtitle>Hermes dispatches bounded Praxis tasks through authenticated queue records.</CardSubtitle>
          <div className="mt-4 space-y-3 text-sm text-slate-300">
            {queueTasks.slice(0, 4).map((task) => (
              <div key={task.id} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <div className="font-medium">{task.task_type}</div>
                    <div className="mt-1 text-slate-400">{task.status} · {task.trace_id ?? 'no trace'}</div>
                  </div>
                  <Badge tone={task.status === 'completed' ? 'success' : task.status === 'failed' ? 'warning' : 'neutral'}>{task.status}</Badge>
                </div>
              </div>
            ))}
            {queueTasks.length === 0 ? <div className="rounded-2xl border border-dashed border-white/10 bg-black/10 p-4 text-slate-400">No queued tasks yet.</div> : null}
          </div>
        </Card>
        <Card>
          <CardTitle>Pipeline guardrails</CardTitle>
          <CardSubtitle>Approval gates stay explicit in UI and API boundaries.</CardSubtitle>
          <div className="mt-4 space-y-3 text-sm text-slate-300">
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">Discovery tasks may enqueue automatically, but external sends and submissions stay manual.</div>
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">Worker completion is visible through queue records and audit events.</div>
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">Supabase RLS keeps owner-scoped data isolated at the database layer.</div>
          </div>
        </Card>
      </section>
    </div>
  );
}
