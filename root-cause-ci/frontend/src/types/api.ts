export interface User {
  id: number;
  full_name: string;
  email: string;
  github_username?: string | null;
  role: string;
  has_github_token: boolean;
  github_token_hint?: string | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Repository {
  id: number;
  name: string;
  full_name: string;
  description: string;
  html_url: string;
  private: boolean;
  updated_at: string;
  default_branch?: string | null;
  latest_run_id?: number | null;
  latest_run_status?: string | null;
  latest_run_conclusion?: string | null;
  latest_run_name?: string | null;
  latest_run_at?: string | null;
}

export interface WorkflowRun {
  id: number;
  name?: string | null;
  run_number?: number | null;
  status?: string | null;
  conclusion?: string | null;
  branch?: string | null;
  head_sha?: string | null;
  commit_message: string;
  actor?: string | null;
  event?: string | null;
  created_at?: string | null;
  html_url?: string | null;
}

export interface EvaluationSummary {
  summary: {
    scenarios: number;
    classification_accuracy: [number, number];
    attribution_top1: [number, number];
    attribution_top3: [number, number];
    baseline_latest_commit_top1: [number, number];
    flaky_detected: [number, number];
    flaky_false_positives: [number, number];
    target_file_accuracy: [number, number];
  };
  note: string;
}
