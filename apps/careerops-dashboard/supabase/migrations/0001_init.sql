create extension if not exists "pgcrypto";

create table if not exists public.jobs (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  canonical_key text unique not null,
  company text not null,
  title text not null,
  location text,
  remote_policy text,
  industry text,
  source text not null,
  job_url text not null,
  application_url text,
  ats text,
  requisition_id text,
  description text,
  posted_at timestamptz,
  closes_at timestamptz,
  salary_min_usd integer,
  salary_max_usd integer,
  total_comp_estimate_usd integer,
  compensation_confidence text check (compensation_confidence in ('high','medium','low','unknown')),
  fit_score numeric(5,2) not null default 0,
  technical_score numeric(5,2),
  leadership_score numeric(5,2),
  industry_score numeric(5,2),
  comp_score numeric(5,2),
  geo_score numeric(5,2),
  status text not null default 'discovered',
  decision text,
  match_summary text,
  missing_requirements text[],
  discovered_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  trace_id text
);

create table if not exists public.applications (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  job_id uuid references public.jobs(id) on delete cascade not null,
  resume_variant_id uuid,
  status text not null default 'materials_pending',
  cover_letter text,
  screening_answers jsonb default '{}'::jsonb,
  submission_confirmed_at timestamptz,
  follow_up_due_at timestamptz,
  owner_notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.approval_requests (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  application_id uuid references public.applications(id) on delete cascade,
  action_type text not null,
  payload jsonb not null,
  status text not null default 'pending',
  approved_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists public.audit_events (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  entity_type text not null,
  entity_id uuid not null,
  actor text not null,
  action text not null,
  payload jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.profile_variants (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  key text not null default 'primary',
  title text not null,
  summary text not null,
  target_titles text[] not null default '{}',
  target_industries text[] not null default '{}',
  compensation_floor_usd integer not null default 200000,
  preferred_total_comp_usd integer not null default 275000,
  geography text[] not null default '{}',
  skills text[] not null default '{}',
  updated_at timestamptz not null default now()
);

create table if not exists public.evidence_bank (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  title text not null,
  scope text not null,
  tech text not null,
  outcome text not null,
  source_ref text not null,
  updated_at timestamptz not null default now()
);

create table if not exists public.queue_tasks (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  task_type text not null,
  payload jsonb not null,
  status text not null default 'queued',
  trace_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists jobs_set_updated_at on public.jobs;
create trigger jobs_set_updated_at before update on public.jobs for each row execute function public.set_updated_at();

drop trigger if exists applications_set_updated_at on public.applications;
create trigger applications_set_updated_at before update on public.applications for each row execute function public.set_updated_at();

drop trigger if exists profile_variants_set_updated_at on public.profile_variants;
create trigger profile_variants_set_updated_at before update on public.profile_variants for each row execute function public.set_updated_at();

drop trigger if exists queue_tasks_set_updated_at on public.queue_tasks;
create trigger queue_tasks_set_updated_at before update on public.queue_tasks for each row execute function public.set_updated_at();

alter table public.jobs enable row level security;
alter table public.applications enable row level security;
alter table public.approval_requests enable row level security;
alter table public.audit_events enable row level security;
alter table public.profile_variants enable row level security;
alter table public.evidence_bank enable row level security;
alter table public.queue_tasks enable row level security;

drop policy if exists "jobs_select_own" on public.jobs;
drop policy if exists "jobs_insert_own" on public.jobs;
drop policy if exists "jobs_update_own" on public.jobs;
create policy "jobs_select_own" on public.jobs for select using (auth.uid() = owner_id);
create policy "jobs_insert_own" on public.jobs for insert with check (auth.uid() = owner_id);
create policy "jobs_update_own" on public.jobs for update using (auth.uid() = owner_id) with check (auth.uid() = owner_id);

drop policy if exists "applications_select_own" on public.applications;
drop policy if exists "applications_insert_own" on public.applications;
drop policy if exists "applications_update_own" on public.applications;
create policy "applications_select_own" on public.applications for select using (auth.uid() = owner_id);
create policy "applications_insert_own" on public.applications for insert with check (auth.uid() = owner_id);
create policy "applications_update_own" on public.applications for update using (auth.uid() = owner_id) with check (auth.uid() = owner_id);

drop policy if exists "approval_requests_select_own" on public.approval_requests;
drop policy if exists "approval_requests_insert_own" on public.approval_requests;
drop policy if exists "approval_requests_update_own" on public.approval_requests;
create policy "approval_requests_select_own" on public.approval_requests for select using (auth.uid() = owner_id);
create policy "approval_requests_insert_own" on public.approval_requests for insert with check (auth.uid() = owner_id);
create policy "approval_requests_update_own" on public.approval_requests for update using (auth.uid() = owner_id) with check (auth.uid() = owner_id);

drop policy if exists "audit_events_select_own" on public.audit_events;
drop policy if exists "audit_events_insert_own" on public.audit_events;
create policy "audit_events_select_own" on public.audit_events for select using (auth.uid() = owner_id);
create policy "audit_events_insert_own" on public.audit_events for insert with check (auth.uid() = owner_id);

drop policy if exists "profile_variants_select_own" on public.profile_variants;
drop policy if exists "profile_variants_insert_own" on public.profile_variants;
drop policy if exists "profile_variants_update_own" on public.profile_variants;
create policy "profile_variants_select_own" on public.profile_variants for select using (auth.uid() = owner_id);
create policy "profile_variants_insert_own" on public.profile_variants for insert with check (auth.uid() = owner_id);
create policy "profile_variants_update_own" on public.profile_variants for update using (auth.uid() = owner_id) with check (auth.uid() = owner_id);

drop policy if exists "evidence_bank_select_own" on public.evidence_bank;
drop policy if exists "evidence_bank_insert_own" on public.evidence_bank;
drop policy if exists "evidence_bank_update_own" on public.evidence_bank;
create policy "evidence_bank_select_own" on public.evidence_bank for select using (auth.uid() = owner_id);
create policy "evidence_bank_insert_own" on public.evidence_bank for insert with check (auth.uid() = owner_id);
create policy "evidence_bank_update_own" on public.evidence_bank for update using (auth.uid() = owner_id) with check (auth.uid() = owner_id);

drop policy if exists "queue_tasks_select_own" on public.queue_tasks;
drop policy if exists "queue_tasks_insert_own" on public.queue_tasks;
drop policy if exists "queue_tasks_update_own" on public.queue_tasks;
create policy "queue_tasks_select_own" on public.queue_tasks for select using (auth.uid() = owner_id);
create policy "queue_tasks_insert_own" on public.queue_tasks for insert with check (auth.uid() = owner_id);
create policy "queue_tasks_update_own" on public.queue_tasks for update using (auth.uid() = owner_id) with check (auth.uid() = owner_id);
