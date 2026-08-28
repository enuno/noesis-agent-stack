import { NextResponse } from 'next/server';
import { getOwnerId } from '@/lib/auth';
import { getDashboardMetrics } from '@/lib/store';

export async function GET() {
  const ownerId = await getOwnerId();
  const metrics = await getDashboardMetrics(ownerId);
  return NextResponse.json(metrics, { headers: { 'cache-control': 'no-store' } });
}
