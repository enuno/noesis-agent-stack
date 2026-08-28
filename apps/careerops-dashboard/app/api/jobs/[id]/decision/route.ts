import { NextResponse } from 'next/server';
import { z } from 'zod';
import { getOwnerId } from '@/lib/auth';
import { updateJobDecision } from '@/lib/store';

const schema = z.object({ decision: z.enum(['pursue', 'watch', 'reject', 'needs_research']) });

async function handle(request: Request, params: { id: string }) {
  const { id } = params;
  const payload = schema.parse(await request.json());
  const ownerId = await getOwnerId();
  const job = await updateJobDecision(id, payload.decision, ownerId);
  return NextResponse.json({ job }, { headers: { 'cache-control': 'no-store' } });
}

export async function POST(request: Request, { params }: { params: { id: string } }) {
  return handle(request, params);
}

export async function PATCH(request: Request, { params }: { params: { id: string } }) {
  return handle(request, params);
}
