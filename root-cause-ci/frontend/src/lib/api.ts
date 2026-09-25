import type { AnalysisReport } from '../types/analysis';
import type { EvaluationSummary, Repository, TokenResponse, User, WorkflowRun } from '../types/api';

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
const TOKEN_KEY = 'rcci.session';

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export const session = {
  get(): string | null {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set(token: string) {
    try {
      localStorage.setItem(TOKEN_KEY, token);
    } catch {
      /* private mode: the session lasts until the tab closes */
    }
  },
  clear() {
    try {
      localStorage.removeItem(TOKEN_KEY);
    } catch {
      /* ignore */
    }
  },
};

/** Fired when the server rejects the stored session, so the app can return to sign-in. */
export const SESSION_EXPIRED_EVENT = 'rcci:session-expired';

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = session.get();
  const headers = new Headers(init.headers);
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  if (token) headers.set('Authorization', `Bearer ${token}`);

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  } catch {
    throw new ApiError('The Root Cause CI server could not be reached. Check that the backend is running.', 0);
  }

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = typeof body?.detail === 'string'
      ? body.detail
      : Array.isArray(body?.detail) ? 'Some of the details you entered are not valid.' : `Request failed (${response.status}).`;
    if (response.status === 401 && token) {
      session.clear();
      window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
    }
    throw new ApiError(detail, response.status);
  }
  return response.json() as Promise<T>;
}

const json = (body: unknown) => JSON.stringify(body);

export const api = {
  register: (body: { full_name: string; email: string; password: string; github_username?: string; github_token?: string; role: string }) =>
    request<TokenResponse>('/auth/register', { method: 'POST', body: json(body) }),
  login: (email: string, password: string) =>
    request<TokenResponse>('/auth/login', { method: 'POST', body: json({ email, password }) }),
  me: () => request<User>('/auth/me'),
  updateProfile: (body: Record<string, unknown>) => request<User>('/auth/me', { method: 'PUT', body: json(body) }),
  verifyGitHub: (github_username?: string, github_token?: string) =>
    request<{ valid: boolean; message: string; avatar_url?: string | null }>('/auth/verify-github', {
      method: 'POST',
      body: json({ github_username, github_token }),
    }),

  repositories: () => request<{ repositories: Repository[] }>('/repositories'),
  runs: (fullName: string) => request<{ runs: WorkflowRun[] }>(`/repositories/${fullName}/runs`),

  analyze: (repository: string, runId: number) =>
    request<AnalysisReport & { message?: string }>('/analysis/github', { method: 'POST', body: json({ repository, run_id: runId }) }),
  history: () => request<{ reports: AnalysisReport[] }>('/analysis/history').then((d) => d.reports ?? []),
  report: (id: number) => request<AnalysisReport>(`/analysis/reports/${id}`),

  createFixPullRequest: (reportId: number) =>
    request<AnalysisReport>('/patches/create-pr', { method: 'POST', body: json({ report_id: reportId }) }),
  checkVerification: (reportId: number) => request<AnalysisReport>(`/patches/${reportId}/verification`),

  evaluation: () => request<EvaluationSummary>('/evaluation/summary'),
};
