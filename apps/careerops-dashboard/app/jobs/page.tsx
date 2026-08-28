import Link from 'next/link';
import { redirect } from 'next/navigation';
import { Badge, Card, CardSubtitle, CardTitle, Button } from '@/components/ui';
import { formatDate, formatCurrency } from '@/lib/utils';
import { getOwnerId } from '@/lib/auth';
import { listJobs } from '@/lib/store';

export default async function JobsPage({ searchParams }: { searchParams?: { status?: string; min_fit?: string } }) {
  const params = searchParams ?? {};
  const ownerId = await getOwnerId().catch(() => null);
  if (!ownerId) redirect('/login?next=/jobs');
  const jobs = await listJobs({ status: params.status, minFit: params.min_fit ? Number(params.min_fit) : undefined, ownerId });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Job Pipeline</h1>
          <p className="mt-2 text-sm text-slate-300">Kanban-first review table with inspectable fit scores and approval-gated actions.</p>
        </div>
        <div className="flex gap-2">
          <Button>Run discovery</Button>
          <Button variant="secondary">Export CSV</Button>
        </div>
      </div>

      <Card>
        <CardTitle>Qualified queue</CardTitle>
        <CardSubtitle>Sort, filter, and decide: pursue, watch, reject, or needs research.</CardSubtitle>
        <div className="mt-5 overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="text-slate-400">
              <tr className="border-b border-white/10">
                <th className="py-3 pr-4">Company</th>
                <th className="py-3 pr-4">Title</th>
                <th className="py-3 pr-4">Location</th>
                <th className="py-3 pr-4">Fit</th>
                <th className="py-3 pr-4">Comp</th>
                <th className="py-3 pr-4">Close</th>
                <th className="py-3 pr-4">Decision</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job.id} className="border-b border-white/5">
                  <td className="py-4 pr-4 font-medium">{job.company}</td>
                  <td className="py-4 pr-4">
                    <Link href={`/jobs/${job.id}`} className="text-sky-200 hover:underline">
                      {job.title}
                    </Link>
                  </td>
                  <td className="py-4 pr-4 text-slate-300">{job.location ?? '—'}</td>
                  <td className="py-4 pr-4">{job.fit_score.toFixed(1)}</td>
                  <td className="py-4 pr-4">{formatCurrency(job.salary_min_usd)} — {formatCurrency(job.salary_max_usd)}</td>
                  <td className="py-4 pr-4 text-slate-300">{formatDate(job.closes_at)}</td>
                  <td className="py-4 pr-4">
                    <Badge tone={job.decision === 'pursue' ? 'success' : job.decision === 'needs_research' ? 'warning' : 'neutral'}>{job.decision ?? 'watch'}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
