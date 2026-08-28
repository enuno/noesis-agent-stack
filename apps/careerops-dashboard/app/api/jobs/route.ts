import { NextResponse } from 'next/server';
import { getOwnerId } from '@/lib/auth';
import { listJobs } from '@/lib/store';

export async function GET(request: Request) {
  const url = new URL(request.url);
  const status = url.searchParams.get('status') ?? undefined;
  const minFit = url.searchParams.get('min_fit');
  const ownerId = await getOwnerId();
  const jobs = await listJobs({ status, minFit: minFit ? Number(minFit) : undefined, ownerId });
  return NextResponse.json({ jobs }, { headers: { 'cache-control': 'no-store' } });
}
