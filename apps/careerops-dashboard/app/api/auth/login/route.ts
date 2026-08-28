import { NextResponse } from 'next/server';
import { z } from 'zod';
import { loginWithPassword, setAuthCookies } from '@/lib/auth';

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});

export async function POST(request: Request) {
  const body = schema.parse(await request.json());
  const session = await loginWithPassword(body.email, body.password);
  const response = NextResponse.json({ user: session.user }, { headers: { 'cache-control': 'no-store' } });
  setAuthCookies(response, session);
  return response;
}
