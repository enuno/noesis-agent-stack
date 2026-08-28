import { NextResponse } from 'next/server';
import { z } from 'zod';
import { getOwnerId } from '@/lib/auth';
import { enqueueQueueTask, listQueueTasks } from '@/lib/store';

const enqueueSchema = z.object({
  task_type: z.string().min(1),
  payload: z.record(z.unknown()).default({}),
});

export async function GET() {
  const ownerId = await getOwnerId();
  const tasks = await listQueueTasks(ownerId);
  return NextResponse.json({ tasks }, { headers: { 'cache-control': 'no-store' } });
}

export async function POST(request: Request) {
  const ownerId = await getOwnerId();
  const payload = enqueueSchema.parse(await request.json());
  const task = await enqueueQueueTask(payload.task_type, payload.payload, ownerId);
  return NextResponse.json({ task }, { headers: { 'cache-control': 'no-store' } });
}
