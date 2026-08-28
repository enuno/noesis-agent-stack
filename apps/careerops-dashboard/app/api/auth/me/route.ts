import { NextResponse } from 'next/server';
import { getOwnerId, getSessionUser } from '@/lib/auth';

export async function GET() {
  try {
    const [user, ownerId] = await Promise.all([getSessionUser(), getOwnerId()]);
    return NextResponse.json({ user, ownerId }, { headers: { 'cache-control': 'no-store' } });
  } catch {
    return NextResponse.json({ user: null, ownerId: null }, { headers: { 'cache-control': 'no-store' } });
  }
}
