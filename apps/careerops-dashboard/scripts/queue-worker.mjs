#!/usr/bin/env node
const baseUrl = (process.env.CAREEROPS_BASE_URL || 'http://127.0.0.1:3000').replace(/\/$/, '');
const workerToken = process.env.CAREEROPS_WORKER_TOKEN;

if (!workerToken) {
  console.error('CAREEROPS_WORKER_TOKEN is required');
  process.exit(1);
}

const idleDelayMs = Number(process.env.CAREEROPS_WORKER_IDLE_DELAY_MS || 10000);
const errorDelayMs = Number(process.env.CAREEROPS_WORKER_ERROR_DELAY_MS || 30000);

async function once() {
  const response = await fetch(`${baseUrl}/api/queue/process`, {
    method: 'POST',
    headers: {
      authorization: `Bearer ${workerToken}`,
      'content-type': 'application/json',
    },
    body: JSON.stringify({}),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || `Worker request failed with ${response.status}`);
  }
  return payload;
}

async function main() {
  for (;;) {
    try {
      const result = await once();
      if (result.processed) {
        console.log(JSON.stringify(result));
        continue;
      }
      await new Promise((resolve) => setTimeout(resolve, idleDelayMs));
    } catch (error) {
      console.error(error instanceof Error ? error.message : String(error));
      await new Promise((resolve) => setTimeout(resolve, errorDelayMs));
    }
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.stack || error.message : String(error));
  process.exit(1);
});
