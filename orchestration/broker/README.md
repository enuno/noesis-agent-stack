# Hermes-OpenClaw Broker

The broker is the sole control plane for managing OpenClaw workers. Hermes and other platform services submit typed jobs through this API; the broker validates schemas, enforces scopes, tracks state, and emits structured events.

## Architecture

```
+----------------+     POST /v1/jobs      +--------+     dispatch      +------------------+
|   main-hermes  | ----------------------> | Broker | ---------------> | research-openclaw|
|  (supervisor)  |                        |        |                  | subconscious-openclaw|
+----------------+                        |        |                  | coder            |
       ^                                  |        |                  | qa               |
       | GET /v1/jobs/{id}                |        |                  +------------------+
       +----------------------------------+        |
                                              +----v----+
                                              |  Store  |
                                              |(memory) |
                                              +---------+
```

## Install

```bash
cd orchestration/broker
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8787
```

## Test

```bash
pytest tests/ -v
```

## API Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | /v1/jobs | Submit a typed job to a worker |
| GET | /v1/jobs/{job_id} | Fetch job status |
| POST | /v1/jobs/{job_id}/cancel | Cancel a running or queued job |
| GET | /v1/jobs/{job_id}/events | Fetch job event stream |
| GET | /v1/jobs/{job_id}/artifacts | List job artifacts |
| GET | /v1/workers | List registered workers and capabilities |
| GET | /v1/health | Control-plane health |

## Worker Registry

| Worker | Runtime | Modes | Read Scopes | Write Scopes |
|---|---|---|---|---|
| research-openclaw | openclaw | refresh, bootstrap, drift-from-research | workspace/research-vault | workspace/research-vault |
| subconscious-openclaw | openclaw | digest, walk, targeted-query | workspace/research-vault, workspace/subconscious-room | workspace/subconscious-room |
| coder | openclaw | build, audit | workspace/coder-jobs, workspace/research-vault, workspace/subconscious-room | workspace/coder-jobs |
| qa | openclaw | audit, validate | workspace/qa-reports, workspace/coder-jobs | workspace/qa-reports |

## Exit criteria

- Broker accepts and validates typed requests against schemas.
- Job IDs, correlation IDs, read scopes, and write scopes are enforced.
- Worker registry and health endpoints are operational.
