import { NextResponse } from 'next/server';
import { clearAuthCookies } from '@/lib/auth';

export async function POST() {
  const response = NextResponse.json({ ok: true }, { headers: { 'cache-control': 'no-store' } });
  clearAuthCookies(response);
  return response;
}
