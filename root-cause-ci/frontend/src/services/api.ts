import type { AnalysisReport } from '../types/analysis';
import type { HealthResponse } from '../types/health';

export const baseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

function authHeaders(json = false): HeadersInit {
  const token = localStorage.getItem('access_token');
  return {
    ...(json ? { 'Content-Type': 'application/json' } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function request<T>(path: string, init: RequestInit = {}, fallbackError = 'Request failed'): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, init);
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: fallbackError }));
    throw new Error(typeof err.detail === 'string' ? err.detail : fallbackError);
  }
  return response.json() as Promise<T>;
}

export function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/health', {}, 'Health request failed');
}

export function postGitHubAnalysis(repository: string, runId: number): Promise<AnalysisReport> {
  return request<AnalysisReport>(
    '/analysis/github',
    { method: 'POST', headers: authHeaders(true), body: JSON.stringify({ repository, run_id: runId }) },
    'GitHub pipeline analysis failed',
  );
}

export async function fetchAnalysisHistory(): Promise<AnalysisReport[]> {
  const data = await request<{ reports: AnalysisReport[] }>('/analysis/history', { headers: authHeaders() }, 'Failed to load history');
  return data.reports ?? [];
}

export function fetchRepositories(): Promise<{ repositories: RepositorySummary[] }> {
  return request('/repositories', { headers: authHeaders() }, 'Failed to fetch repositories');
}

export function createFixPullRequest(reportId: number): Promise<AnalysisReport> {
  return request<AnalysisReport>(
    '/patches/create-pr',
    { method: 'POST', headers: authHeaders(true), body: JSON.stringify({ report_id: reportId }) },
    'Failed to create pull request',
  );
}

export function checkVerification(reportId: number): Promise<AnalysisReport> {
  return request<AnalysisReport>(`/patches/${reportId}/verification`, { headers: authHeaders() }, 'Failed to check verification');
}

export interface RepositorySummary {
  id: number;
  name: string;
  full_name: string;
  description?: string | null;
  html_url: string;
  updated_at: string;
  latest_run_id?: number | null;
  latest_run_status?: string | null;
  latest_run_conclusion?: string | null;
}
