import { NextResponse } from 'next/server';
import { z } from 'zod';
import { getOwnerId } from '@/lib/auth';
import { updateApplicationMaterials } from '@/lib/store';

const schema = z.object({
  cover_letter: z.string().optional(),
  resume_variant_id: z.string().optional(),
  owner_notes: z.string().optional(),
  screening_answers: z.record(z.unknown()).optional(),
});

async function handler(request: Request, params: { id: string }) {
  const { id } = params;
  const payload = schema.parse(await request.json());
  const ownerId = await getOwnerId();
  const application = await updateApplicationMaterials(id, payload, ownerId);
  return NextResponse.json({ application }, { headers: { 'cache-control': 'no-store' } });
}

export async function POST(request: Request, { params }: { params: { id: string } }) {
  return handler(request, params);
}

export async function PATCH(request: Request, { params }: { params: { id: string } }) {
  return handler(request, params);
}
