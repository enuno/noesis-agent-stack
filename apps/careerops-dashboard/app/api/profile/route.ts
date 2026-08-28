import { NextResponse } from 'next/server';
import { z } from 'zod';
import { getOwnerId } from '@/lib/auth';
import { getProfile, updateProfile } from '@/lib/store';

const schema = z.object({
  title: z.string().min(1).optional(),
  summary: z.string().min(1).optional(),
  compensation_floor_usd: z.number().int().optional(),
  preferred_total_comp_usd: z.number().int().optional(),
  target_titles: z.array(z.string()).optional(),
  target_industries: z.array(z.string()).optional(),
  geography: z.array(z.string()).optional(),
  skills: z.array(z.string()).optional(),
});

export async function GET() {
  const ownerId = await getOwnerId().catch(() => null);
  if (!ownerId) return NextResponse.json({ profile: null }, { headers: { 'cache-control': 'no-store' } });
  const profile = await getProfile(ownerId);
  return NextResponse.json({ profile }, { headers: { 'cache-control': 'no-store' } });
}

export async function PATCH(request: Request) {
  const ownerId = await getOwnerId();
  const payload = schema.parse(await request.json());
  const profile = await updateProfile(ownerId, payload);
  return NextResponse.json({ profile }, { headers: { 'cache-control': 'no-store' } });
}
