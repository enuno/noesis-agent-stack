import { Card, CardSubtitle, CardTitle, Badge, Button } from '@/components/ui';
import { redirect } from 'next/navigation';
import { getOwnerId } from '@/lib/auth';
import { getEvidence, getProfile } from '@/lib/store';
import { formatDate, formatCurrency } from '@/lib/utils';

export default async function ProfilePage() {
  const ownerId = await getOwnerId().catch(() => null);
  if (!ownerId) redirect('/login?next=/profile');
  const [profile, evidence] = await Promise.all([getProfile(ownerId), getEvidence(ownerId)]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Profile & Evidence Bank</h1>
        <p className="mt-2 text-sm text-slate-300">Editable profile surface for target roles, compensation, geography, and verified evidence.</p>
      </div>

      <section className="grid gap-4 xl:grid-cols-[1.1fr_1fr]">
        <Card>
          <CardTitle>Target profile</CardTitle>
          <CardSubtitle>{profile?.summary ?? 'Profile unavailable'}</CardSubtitle>
          <div className="mt-4 grid gap-3 md:grid-cols-2 text-sm">
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase tracking-[0.22em] text-slate-400">Target titles</div>
              <div className="mt-2 space-y-1 text-slate-200">{profile?.target_titles.map((item) => <div key={item}>{item}</div>)}</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase tracking-[0.22em] text-slate-400">Compensation</div>
              <div className="mt-2 text-slate-200">Floor {formatCurrency(profile?.compensation_floor_usd ?? null)}</div>
              <div className="text-slate-300">Preferred total {formatCurrency(profile?.preferred_total_comp_usd ?? null)}</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4 md:col-span-2">
              <div className="text-xs uppercase tracking-[0.22em] text-slate-400">Skills</div>
              <div className="mt-2 flex flex-wrap gap-2">{profile?.skills.map((skill) => <Badge key={skill}>{skill}</Badge>)}</div>
            </div>
          </div>
          <div className="mt-5 flex gap-2">
            <Button>Save profile</Button>
            <Button variant="secondary">Load YAML</Button>
          </div>
        </Card>

        <Card>
          <CardTitle>Evidence bank</CardTitle>
          <CardSubtitle>Verified accomplishment snippets for drafts and application answers.</CardSubtitle>
          <div className="mt-4 space-y-3">
            {evidence.map((item) => (
              <div key={item.id} className="rounded-2xl border border-white/10 bg-black/20 p-4 text-sm">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="font-medium">{item.title}</div>
                    <div className="mt-1 text-slate-300">{item.scope}</div>
                  </div>
                  <Badge tone="info">{formatDate(item.updated_at)}</Badge>
                </div>
                <div className="mt-3 text-slate-300">{item.tech}</div>
                <div className="mt-2 text-slate-200">{item.outcome}</div>
                <div className="mt-2 text-xs uppercase tracking-[0.22em] text-slate-400">Source: {item.source_ref}</div>
              </div>
            ))}
          </div>
        </Card>
      </section>
    </div>
  );
}
