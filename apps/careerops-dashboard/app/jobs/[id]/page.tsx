import Link from 'next/link';
import { notFound } from 'next/navigation';
import { redirect } from 'next/navigation';
import { Badge, Card, CardSubtitle, CardTitle, Button, ProgressBar } from '@/components/ui';
import { getOwnerId } from '@/lib/auth';
import { buildApplicationPacket, getJob, getProfile } from '@/lib/store';
import { formatDate, formatCurrency } from '@/lib/utils';

export default async function JobDetailPage({ params }: { params: { id: string } }) {
  const { id } = params;
  const ownerId = await getOwnerId().catch(() => null);
  if (!ownerId) redirect(`/login?next=/jobs/${encodeURIComponent(id)}`);
  const [job, profile] = await Promise.all([getJob(id, ownerId), getProfile(ownerId)]);
  if (!job) notFound();
  const packet = profile ? buildApplicationPacket(job, profile) : null;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap gap-2">
            <Badge tone="info">{job.status}</Badge>
            <Badge tone={job.decision === 'pursue' ? 'success' : job.decision === 'needs_research' ? 'warning' : 'neutral'}>{job.decision ?? 'watch'}</Badge>
          </div>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight">{job.company} · {job.title}</h1>
          <p className="mt-2 text-sm text-slate-300">{job.location ?? 'Location unknown'} · {job.remote_policy ?? 'remote policy unknown'} · posted {formatDate(job.posted_at)}</p>
        </div>
        <div className="flex gap-2">
          <Button>Request packet</Button>
          <Button variant="secondary">Approve application assistance</Button>
        </div>
      </div>

      <section className="grid gap-4 md:grid-cols-4">
        <Card><CardTitle>{job.fit_score.toFixed(1)}</CardTitle><CardSubtitle>fit score</CardSubtitle><ProgressBar value={job.fit_score} /></Card>
        <Card><CardTitle>{job.technical_score?.toFixed(1) ?? '—'}</CardTitle><CardSubtitle>technical</CardSubtitle></Card>
        <Card><CardTitle>{job.leadership_score?.toFixed(1) ?? '—'}</CardTitle><CardSubtitle>leadership</CardSubtitle></Card>
        <Card><CardTitle>{job.geo_score?.toFixed(1) ?? '—'}</CardTitle><CardSubtitle>geo</CardSubtitle></Card>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.5fr_1fr]">
        <Card>
          <CardTitle>Requirement-to-evidence matrix</CardTitle>
          <CardSubtitle>Explain fit by mapping requirements to evidence from the profile bank.</CardSubtitle>
          <div className="mt-4 space-y-3 text-sm">
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <div className="font-medium text-sky-200">Why this is a match</div>
              <p className="mt-2 text-slate-300">{job.match_summary ?? 'Strong overlap with the AI-agent / infrastructure leadership profile.'}</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <div className="font-medium text-amber-200">Gaps / risks</div>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-slate-300">
                {(job.missing_requirements ?? ['None captured']).map((item) => <li key={item}>{item}</li>)}
              </ul>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <div className="font-medium text-emerald-200">Compensation</div>
              <p className="mt-2 text-slate-300">{formatCurrency(job.salary_min_usd)} — {formatCurrency(job.salary_max_usd)} · confidence {job.compensation_confidence ?? 'unknown'}</p>
            </div>
          </div>
        </Card>

        <Card>
          <CardTitle>Action surface</CardTitle>
          <CardSubtitle>All external writes stay approval-gated.</CardSubtitle>
          <div className="mt-4 space-y-3 text-sm text-slate-300">
            <a href={job.job_url} target="_blank" rel="noreferrer" className="block rounded-2xl border border-white/10 bg-black/20 p-3 hover:border-sky-400/40">Open source job page</a>
            {job.application_url ? <a href={job.application_url} target="_blank" rel="noreferrer" className="block rounded-2xl border border-white/10 bg-black/20 p-3 hover:border-sky-400/40">Open application page</a> : null}
            <div className="rounded-2xl border border-amber-400/20 bg-amber-400/10 p-3 text-amber-50">Submission remains disabled until approval is explicit for this application.</div>
            <div className="rounded-2xl border border-white/10 bg-black/20 p-3">ATS: {job.ats ?? 'unknown'} · Req ID: {job.requisition_id ?? 'unknown'}</div>
          </div>
        </Card>
      </section>

      {packet ? (
        <Card>
          <CardTitle>Draft packet preview</CardTitle>
          <CardSubtitle>Generated from the profile and job record; no silent modifications.</CardSubtitle>
          <pre className="mt-4 overflow-x-auto whitespace-pre-wrap rounded-2xl border border-white/10 bg-black/20 p-4 text-sm text-slate-200">{packet.fitBrief}</pre>
        </Card>
      ) : null}
    </div>
  );
}
