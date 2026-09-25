export interface Frame {
  file: string;
  line: number;
  function?: string | null;
}

export interface JobAnalysis {
  id: number;
  name: string;
  conclusion: string;
  html_url?: string;
  failed_step?: string | null;
  log_available: boolean;
  category: string;
  confidence: number;
  explanation: string;
  signals: string[];
  error_message?: string | null;
  failed_tests: string[];
  error_signatures: { name: string; matched_text?: string }[];
  frames: Frame[];
  key_lines: string[];
}

export interface FlakyInfo {
  flaky_probability: number;
  classification: string;
  evidence: { signal: string; observed_value: string; score_contribution: number; explanation: string }[];
  historical_runs: string[];
  same_commit_passed: boolean;
  runs_considered: number;
}

export interface CandidateCommit {
  commit_sha: string;
  message: string;
  author?: string | null;
  date?: string | null;
  changed_files: string[];
  changed_functions: string[];
  confidence_score: number;
  signals: Record<string, number>;
  reasons: Record<string, string>;
}

export interface EvidenceItem {
  signal: string;
  explanation: string;
  score_contribution: number;
}

export interface PatchInfo {
  status: 'generated' | 'rejected' | 'skipped' | 'error';
  file_path?: string | null;
  summary?: string | null;
  diff?: string | null;
  reason?: string | null;
}

export interface VerificationInfo {
  status: 'pending' | 'running' | 'verified' | 'failed';
  detail: string;
  runs: { id: number; name?: string; status?: string; conclusion?: string | null; url?: string }[];
}

export interface AnalysisReport {
  report_id: number;
  repository: string;
  run_id: string;
  job_name: string;
  branch?: string | null;
  source: 'manual' | 'webhook' | string;
  is_healthy: boolean;
  classification: { category: string; explanation: string; confidence?: number | null };
  llm_summary?: string | null;
  report_preview?: string | null;
  pr_title?: string | null;
  pr_number?: number | null;
  author?: string | null;
  comment_posted: boolean;
  created_at?: string | null;
  run?: { url?: string; workflow?: string; head_sha?: string; run_number?: number; event?: string } | null;
  jobs: JobAnalysis[];
  primary_job?: string | null;
  flaky?: FlakyInfo | null;
  base_sha?: string | null;
  candidates: CandidateCommit[];
  evidence_chain: EvidenceItem[];
  confidence_score?: number | null;
  target_file?: string | null;
  patch?: PatchInfo | null;
  warnings: string[];
  fix_pr_url?: string | null;
  fix_pr_number?: number | null;
  fix_branch?: string | null;
  verification_status?: VerificationInfo['status'] | null;
  verification?: VerificationInfo | null;
}
