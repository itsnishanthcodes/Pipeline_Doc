import type { HealthResponse } from '../types/health';

const baseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export interface WebhookPayloadInput {
  repository: string;
  workflow: string;
  branch: string;
  commit_sha: string;
  log_excerpt: string;
  historical_runs: string[];
}

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${baseUrl}/health`);
  if (!response.ok) {
    throw new Error(`Health request failed with status ${response.status}`);
  }
  return response.json() as Promise<HealthResponse>;
}

export async function postGitHubWebhook(payload: WebhookPayloadInput) {
  const requestBody = {
    repository: { full_name: payload.repository },
    workflow_run: {
      id: Date.now(),
      name: payload.workflow,
      head_branch: payload.branch,
      head_sha: payload.commit_sha,
      status: 'completed',
      conclusion: 'failure',
      run_started_at: new Date().toISOString(),
    },
    historical_runs: payload.historical_runs,
    log_excerpt: payload.log_excerpt,
  };

  const response = await fetch(`${baseUrl}/webhooks/github`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-GitHub-Event': 'workflow_run',
      'X-GitHub-Delivery': `delivery-${Date.now()}`,
    },
    body: JSON.stringify(requestBody),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Webhook request failed' }));
    throw new Error(err.detail || 'Webhook trigger failed');
  }

  return response.json();
}
