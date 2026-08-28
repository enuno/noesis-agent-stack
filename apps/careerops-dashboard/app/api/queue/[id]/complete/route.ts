import { NextResponse } from 'next/server';
import { z } from 'zod';
import { getOwnerId } from '@/lib/auth';
import { completeQueueTask } from '@/lib/store';

const schema = z.object({
  status: z.enum(['completed', 'failed']),
});

export async function POST(request: Request, { params }: { params: { id: string } }) {
  const ownerId = await getOwnerId();
  const payload = schema.parse(await request.json());
  const task = await completeQueueTask(params.id, payload.status, ownerId);
  if (!task) return NextResponse.json({ error: 'Not found' }, { status: 404 });
  return NextResponse.json({ task }, { headers: { 'cache-control': 'no-store' } });
}
