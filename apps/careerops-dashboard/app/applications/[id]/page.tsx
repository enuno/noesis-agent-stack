import { notFound } from 'next/navigation';
import { redirect } from 'next/navigation';
import { Badge, Card, CardSubtitle, CardTitle, Button } from '@/components/ui';
import { getOwnerId } from '@/lib/auth';
import { buildApplicationPacket, getApplication, getJob, getProfile } from '@/lib/store';
import { formatDate } from '@/lib/utils';

export default async function ApplicationPage({ params }: { params: { id: string } }) {
  const { id } = params;
  const ownerId = await getOwnerId().catch(() => null);
  if (!ownerId) redirect(`/login?next=/applications/${encodeURIComponent(id)}`);
  const application = await getApplication(id, ownerId);
  if (!application) notFound();
  const [job, profile] = await Promise.all([getJob(application.job_id, ownerId), getProfile(ownerId)]);
  if (!job || !profile) notFound();
  const packet = buildApplicationPacket(job, profile);

  return (
    <div className="space-y-6">
      <div>
        <div className="flex flex-wrap gap-2">
          <Badge tone="info">{application.status}</Badge>
          <Badge tone="warning">approval-gated</Badge>
        </div>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight">Application Studio</h1>
        <p className="mt-2 text-sm text-slate-300">{job.company} · {job.title} · follow up due {formatDate(application.follow_up_due_at)}</p>
      </div>

      <section className="grid gap-4 xl:grid-cols-[1.2fr_1fr]">
        <Card>
          <CardTitle>Draft packet</CardTitle>
          <CardSubtitle>Editable in later iterations; shown here as the approved draft surface.</CardSubtitle>
          <div className="mt-4 space-y-4">
            <div>
              <label className="text-xs uppercase tracking-[0.22em] text-slate-400">Cover letter draft</label>
              <textarea className="mt-2 min-h-[220px] w-full rounded-2xl border border-white/10 bg-black/30 p-4 text-sm text-slate-100" defaultValue={packet.coverLetterDraft} readOnly />
            </div>
            <div>
              <label className="text-xs uppercase tracking-[0.22em] text-slate-400">Screening answers</label>
              <pre className="mt-2 whitespace-pre-wrap rounded-2xl border border-white/10 bg-black/30 p-4 text-sm text-slate-200">{JSON.stringify(packet.screeningAnswers, null, 2)}</pre>
            </div>
          </div>
        </Card>

        <Card>
          <CardTitle>Checklist</CardTitle>
          <CardSubtitle>Open, review, approve, then assist.</CardSubtitle>
          <ul className="mt-4 space-y-2 text-sm text-slate-300">
            {packet.checklist.map((item) => <li key={item} className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3">{item}</li>)}
          </ul>
          <div className="mt-5 space-y-2">
            <Button className="w-full">Approve packet</Button>
            <Button variant="secondary" className="w-full">Open and assist application</Button>
          </div>
        </Card>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardTitle>Résumé diff</CardTitle>
          <CardSubtitle>Proposed changes are surfaced as a checklist, not silent edits.</CardSubtitle>
        </Card>
        <Card>
          <CardTitle>Resume baseline</CardTitle>
          <CardSubtitle>{application.resume_variant_id ?? 'AI/agent infrastructure variant pending selection'}</CardSubtitle>
        </Card>
        <Card>
          <CardTitle>Trace</CardTitle>
          <CardSubtitle>{packet.traceId}</CardSubtitle>
        </Card>
      </section>
    </div>
  );
}
