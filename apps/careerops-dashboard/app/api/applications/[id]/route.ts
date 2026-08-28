import { NextResponse } from 'next/server';
import { getOwnerId } from '@/lib/auth';
import { getApplication } from '@/lib/store';

export async function GET(_request: Request, { params }: { params: { id: string } }) {
  const { id } = params;
  const ownerId = await getOwnerId();
  const application = await getApplication(id, ownerId);
  if (!application) return NextResponse.json({ error: 'Not found' }, { status: 404 });
  return NextResponse.json({ application }, { headers: { 'cache-control': 'no-store' } });
}
