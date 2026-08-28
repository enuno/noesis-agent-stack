# CareerOps Dashboard

Private Next.js control plane for the Noesis Praxis job-application pipeline.

## Required environment variables

- `NEXT_PUBLIC_SUPABASE_URL` — Supabase project URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` — public Supabase anon key
- `SUPABASE_SERVICE_ROLE_KEY` — server-only admin key for RLS-bypassing writes
- `CAREEROPS_OWNER_ID` — optional explicit owner override for single-user deployments
- `CAREEROPS_WORKER_TOKEN` — bearer token for the queue processor route
- `CAREEROPS_BASE_URL` — base URL used by the local queue worker script
- `NEXT_PUBLIC_DEMO_MODE` — set to `true` for offline demo mode

## Local development

```bash
npm install
npm run dev
```

## Production container

The app is configured for Next.js standalone output and ships with a multi-stage Dockerfile.

```bash
docker build -t careerops-dashboard .
docker run --rm -p 3000:3000 \
  -e NEXT_PUBLIC_SUPABASE_URL=... \
  -e NEXT_PUBLIC_SUPABASE_ANON_KEY=... \
  -e SUPABASE_SERVICE_ROLE_KEY=... \
  -e CAREEROPS_WORKER_TOKEN=... \
  careerops-dashboard
```

## Queue worker

The worker loop posts to `/api/queue/process` with `Authorization: Bearer $CAREEROPS_WORKER_TOKEN`.

```bash
npm run worker
```

## Notes

- Login is handled through Supabase Auth and httpOnly cookies.
- Discovery uses official career pages and public ATS endpoints where available.
- Outreach, uploads, and submission remain approval-gated.
