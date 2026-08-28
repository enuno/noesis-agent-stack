import { NextResponse } from 'next/server';
import { getOwnerId } from '@/lib/auth';
import { createDiscoveryRun } from '@/lib/store';

export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));
  const query = typeof body.query === 'string' && body.query ? body.query : 'Director of AI Platform';
  const sourceSet = Array.isArray(body.sourceSet) && body.sourceSet.length > 0 ? body.sourceSet.map(String) : ['company-careers', 'greenhouse'];
  const ownerId = await getOwnerId();
  const result = await createDiscoveryRun({ query, sourceSet, ownerId });
  return NextResponse.json(result, { headers: { 'cache-control': 'no-store' } });
}
