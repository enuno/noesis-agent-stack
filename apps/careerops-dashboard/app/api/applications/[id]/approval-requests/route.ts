import { NextResponse } from 'next/server';
import { z } from 'zod';
import { getOwnerId } from '@/lib/auth';
import { createApprovalRequest } from '@/lib/store';

const schema = z.object({
  action_type: z.string().min(1),
  payload: z.record(z.unknown()).default({}),
});

export async function POST(request: Request, { params }: { params: { id: string } }) {
  const { id } = params;
  const payload = schema.parse(await request.json());
  const ownerId = await getOwnerId();
  const requestRecord = await createApprovalRequest(id, payload.action_type, payload.payload, ownerId);
  return NextResponse.json({ approval_request: requestRecord }, { headers: { 'cache-control': 'no-store' } });
}
