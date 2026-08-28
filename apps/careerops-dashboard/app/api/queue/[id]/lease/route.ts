import { NextResponse } from 'next/server';
import { getOwnerId } from '@/lib/auth';
import { claimQueueTask } from '@/lib/store';

export async function POST(_request: Request, { params }: { params: { id: string } }) {
  const ownerId = await getOwnerId();
  const task = await claimQueueTask(params.id, ownerId);
  if (!task) return NextResponse.json({ error: 'Not found' }, { status: 404 });
  return NextResponse.json({ task }, { headers: { 'cache-control': 'no-store' } });
}
