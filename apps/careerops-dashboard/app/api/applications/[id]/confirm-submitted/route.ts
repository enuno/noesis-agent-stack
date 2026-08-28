import { NextResponse } from 'next/server';
import { z } from 'zod';
import { getOwnerId } from '@/lib/auth';
import { confirmSubmitted } from '@/lib/store';

const schema = z.object({ follow_up_due_at: z.string().datetime().optional() });

export async function POST(request: Request, { params }: { params: { id: string } }) {
  const { id } = params;
  const payload = schema.parse(await request.json().catch(() => ({})));
  const ownerId = await getOwnerId();
  const application = await confirmSubmitted(id, payload.follow_up_due_at, ownerId);
  return NextResponse.json({ application }, { headers: { 'cache-control': 'no-store' } });
}
