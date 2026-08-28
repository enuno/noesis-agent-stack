import { NextResponse } from 'next/server';
import { getOwnerId } from '@/lib/auth';
import { getJob, getProfile, buildApplicationPacket } from '@/lib/store';

export async function POST(request: Request, { params }: { params: { id: string } }) {
  const { id } = params;
  const body = await request.json().catch(() => ({}));
  const ownerId = await getOwnerId();
  const job = await getJob(id, ownerId);
  const profile = await getProfile(ownerId);
  if (!job || !profile) return NextResponse.json({ error: 'Job or profile not found' }, { status: 404 });
  const packet = buildApplicationPacket(job, profile);
  return NextResponse.json({ application_id: body.applicationId ?? null, job_id: id, packet, allowed_outputs: ['fit_brief', 'cover_letter_draft', 'resume_delta', 'screening_answer_drafts', 'application_checklist'], prohibited_actions: ['send_message', 'upload_document', 'submit_application'] }, { headers: { 'cache-control': 'no-store' } });
}
