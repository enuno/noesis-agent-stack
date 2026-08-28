import { NextResponse } from 'next/server';
import { getOwnerId } from '@/lib/auth';
import { claimQueueTask, completeQueueTask, getJob, listQueueTasks } from '@/lib/store';

export async function POST(request: Request) {
  const workerToken = process.env.CAREEROPS_WORKER_TOKEN;
  if (workerToken) {
    const authHeader = request.headers.get('authorization') ?? '';
    if (authHeader !== `Bearer ${workerToken}`) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }
  }

  const ownerId = process.env.CAREEROPS_OWNER_ID || (await getOwnerId().catch(() => null));
  if (!ownerId) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const queue = await listQueueTasks(ownerId);
  const queued = queue.find((item) => item.status === 'queued');
  if (!queued) {
    return NextResponse.json({ processed: 0, message: 'No queued tasks' }, { headers: { 'cache-control': 'no-store' } });
  }

  const taskRecord = await claimQueueTask(queued.id, ownerId);
  if (!taskRecord) {
    return NextResponse.json({ processed: 0, message: 'Task could not be claimed' }, { headers: { 'cache-control': 'no-store' } });
  }

  let status: 'completed' | 'failed' = 'completed';

  try {
    if (taskRecord.task_type === 'discover_job' && typeof taskRecord.payload.job_id === 'string') {
      await getJob(taskRecord.payload.job_id, ownerId);
    }
  } catch {
    status = 'failed';
  }

  const updated = await completeQueueTask(taskRecord.id, status, ownerId);
  return NextResponse.json({ processed: 1, task: updated }, { headers: { 'cache-control': 'no-store' } });
}
