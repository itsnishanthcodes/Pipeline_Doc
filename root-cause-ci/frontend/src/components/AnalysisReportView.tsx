import React, { useEffect, useRef, useState } from 'react';
import {
  AlertTriangle, CheckCircle, Copy, ExternalLink, GitCommit, GitPullRequest, Loader2,
  Search, ShieldCheck, Terminal, Wrench, XCircle,
} from 'lucide-react';
import { checkVerification, createFixPullRequest } from '../services/api';
import type { AnalysisReport } from '../types/analysis';

interface Props {
  report: AnalysisReport;
  onUpdate?: (report: AnalysisReport) => void;
}

const SIGNAL_LABELS: Record<string, string> = {
  temporal_proximity: 'Recency',
  file_overlap: 'File overlap',
  stack_trace_overlap: 'Stack trace',
  function_overlap: 'Function',
  dependency_relationship: 'Dependency',
  historical_evidence: 'History',
};

const pct = (v?: number | null) => (v === undefined || v === null ? 'n/a' : `${(v * 100).toFixed(0)}%`);
const short = (sha?: string | null) => (sha ? sha.slice(0, 7) : '');

function DiffView({ diff }: { diff: string }) {
  return (
    <pre className="diff-view">
      {diff.split('\n').map((line, i) => {
        const cls = line.startsWith('+++') || line.startsWith('---') ? 'diff-meta'
          : line.startsWith('@@') ? 'diff-hunk'
          : line.startsWith('+') ? 'diff-add'
          : line.startsWith('-') ? 'diff-del' : 'diff-ctx';
        return <div key={i} className={cls}>{line || ' '}</div>;
      })}
    </pre>
  );
}

function VerificationBadge({ status }: { status?: string | null }) {
  if (!status) return null;
  const map: Record<string, { cls: string; label: string; icon: React.ReactNode }> = {
    pending: { cls: 'badge-pending', label: 'Waiting for CI', icon: <Loader2 size={14} className="spin" /> },
    running: { cls: 'badge-pending', label: 'CI running on fix branch', icon: <Loader2 size={14} className="spin" /> },
    verified: { cls: 'badge-green', label: 'Verified: CI passed', icon: <ShieldCheck size={14} /> },
    failed: { cls: 'badge-red', label: 'Verification failed', icon: <XCircle size={14} /> },
  };
  const m = map[status] ?? map.pending;
  return <span className={`status-badge ${m.cls}`}>{m.icon}{m.label}</span>;
}

export const AnalysisReportView: React.FC<Props> = ({ report, onUpdate }) => {
  const [creating, setCreating] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const polls = useRef(0);

  // Poll CI on the fix branch until it is verified or failed (max ~10 minutes).
  useEffect(() => {
    const status = report.verification_status;
    if (!report.fix_branch || (status !== 'pending' && status !== 'running')) return;
    polls.current = 0;
    const timer = window.setInterval(async () => {
      polls.current += 1;
      if (polls.current > 40) { window.clearInterval(timer); return; }
      try {
        const updated = await checkVerification(report.report_id);
        onUpdate?.(updated);
        if (updated.verification_status === 'verified' || updated.verification_status === 'failed') {
          window.clearInterval(timer);
        }
      } catch {
        /* keep polling; transient GitHub errors are expected */
      }
    }, 15000);
    return () => window.clearInterval(timer);
  }, [report.report_id, report.fix_branch, report.verification_status, onUpdate]);

  const handleCreatePr = async () => {
    setCreating(true);
    setActionError(null);
    try {
      onUpdate?.(await createFixPullRequest(report.report_id));
    } catch (e) {
      setActionError(e instanceof Error ? e.message : 'Failed to create pull request');
    } finally {
      setCreating(false);
    }
  };

  const handleCheckNow = async () => {
    setActionError(null);
    try {
      onUpdate?.(await checkVerification(report.report_id));
    } catch (e) {
      setActionError(e instanceof Error ? e.message : 'Failed to check verification');
    }
  };

  const healthy = report.is_healthy;
  const best = report.candidates?.[0];
  const patch = report.patch;

  return (
    <div className="report-view">
      <div className="panel-top">
        <span className="eyebrow">
          {report.source === 'webhook' ? 'Automatic analysis (webhook)' : 'Analysis report'}
          {report.created_at && ` · ${new Date(report.created_at).toLocaleString()}`}
        </span>
        <h3>{report.repository}</h3>
        <p className="workflow-name">
          Run #{report.run_id}{report.run?.workflow && ` · ${report.run.workflow}`}
          {report.branch && <> · branch <code>{report.branch}</code></>}
          {report.run?.url && (
            <a className="inline-link" href={report.run.url} target="_blank" rel="noreferrer">
              View on GitHub <ExternalLink size={12} />
            </a>
          )}
        </p>
      </div>

      <div className="detail-cards-grid">
        <div className="mini-card">
          <span className="label">Classification</span>
          <strong className={healthy ? 'text-emerald' : 'text-cyan'}>
            {healthy ? 'HEALTHY (PASSED)' : report.classification.category}
          </strong>
          {!healthy && <small className="muted-text">{pct(report.classification.confidence)} rule confidence</small>}
        </div>
        {!healthy && report.flaky && (
          <div className="mini-card">
            <span className="label">Flaky-test verdict</span>
            <strong className={report.flaky.classification === 'LIKELY_FLAKY' ? 'text-amber' : 'text-emerald'}>
              {report.flaky.classification.replace(/_/g, ' ')}
            </strong>
            <small className="muted-text">
              {report.flaky.classification === 'INSUFFICIENT_HISTORY'
                ? `only ${report.flaky.runs_considered} earlier run${report.flaky.runs_considered === 1 ? '' : 's'} on this branch`
                : `${pct(report.flaky.flaky_probability)} over ${report.flaky.runs_considered} earlier runs`}
            </small>
          </div>
        )}
        {!healthy && best && (
          <div className="mini-card">
            <span className="label">Most likely commit</span>
            <strong className="text-indigo mono">{short(best.commit_sha)}</strong>
            <small className="muted-text">{pct(report.confidence_score)} confidence</small>
          </div>
        )}
        {report.author && (
          <div className="mini-card">
            <span className="label">Author attribution</span>
            <strong className="text-cyan">@{report.author}</strong>
          </div>
        )}
      </div>

      {!healthy && report.jobs.length > 0 && (
        <section className="report-section">
          <h4><Terminal size={16} /> Failed jobs ({report.jobs.length})</h4>
          {report.jobs.map((job) => (
            <div key={job.id} className={`job-card ${job.name === report.primary_job ? 'primary' : ''}`}>
              <div className="job-card-top">
                <strong>{job.name}</strong>
                {job.failed_step && <span className="muted-text">step: {job.failed_step}</span>}
                <span className="category-tag">{job.category}</span>
                {job.html_url && <a className="inline-link" href={job.html_url} target="_blank" rel="noreferrer">logs <ExternalLink size={12} /></a>}
              </div>
              {job.error_message && <pre className="error-terminal compact">{job.error_message}</pre>}
              {job.failed_tests.length > 0 && (
                <p className="job-meta">Failing tests: {job.failed_tests.map((t) => <code key={t}>{t}</code>)}</p>
              )}
              {job.frames.length > 0 && (
                <p className="job-meta">Stack frames: {job.frames.slice(0, 6).map((f) => (
                  <code key={`${f.file}:${f.line}`}>{f.file}:{f.line}{f.function ? ` (${f.function})` : ''}</code>
                ))}</p>
              )}
              {!job.log_available && <p className="muted-text">Logs were not available for this job.</p>}
            </div>
          ))}
        </section>
      )}

      {!healthy && report.flaky && report.flaky.historical_runs.length > 0 && (
        <section className="report-section">
          <h4><AlertTriangle size={16} /> Job history on this branch (oldest to newest)</h4>
          <div className="history-dots">
            {report.flaky.historical_runs.map((o, i) => (
              <span key={i} className={`dot ${o === 'PASS' ? 'dot-pass' : 'dot-fail'}`} title={o} />
            ))}
          </div>
          {report.flaky.same_commit_passed && (
            <p className="muted-text">Another run of the same commit passed, which points to flakiness.</p>
          )}
        </section>
      )}

      {!healthy && report.candidates.length > 0 && (
        <section className="report-section">
          <h4><GitCommit size={16} /> Candidate commits since the last green run</h4>
          <div className="table-scroll">
            <table className="candidates-table">
              <thead>
                <tr><th>Commit</th><th>Message</th><th>Author</th><th>Confidence</th><th>Signals</th></tr>
              </thead>
              <tbody>
                {report.candidates.map((c, i) => (
                  <tr key={c.commit_sha} className={i === 0 ? 'top-candidate' : ''}>
                    <td className="mono">{short(c.commit_sha)}</td>
                    <td>{c.message}</td>
                    <td>{c.author ?? 'unknown'}</td>
                    <td>
                      <div className="confidence-bar"><span style={{ width: pct(c.confidence_score) }} /></div>
                      {pct(c.confidence_score)}
                    </td>
                    <td>
                      {Object.entries(c.signals).filter(([, v]) => v > 0).map(([k]) => (
                        <span key={k} className="signal-chip" title={c.reasons?.[k]}>{SIGNAL_LABELS[k] ?? k}</span>
                      ))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {report.evidence_chain.length > 0 && (
        <section className="report-section evidence-box">
          <h4><Search size={16} /> Evidence chain for {short(best?.commit_sha)}</h4>
          <ul className="evidence-list">
            {report.evidence_chain.map((ev, idx) => (
              <li key={idx}>
                <CheckCircle size={14} className="text-emerald" />
                <div>
                  <strong>{ev.signal}:</strong> {ev.explanation}
                  <small className="muted-text"> (+{(ev.score_contribution * 100).toFixed(1)}%)</small>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {report.llm_summary && (
        <section className="report-section summary-box">
          <h4><Terminal size={16} /> Root cause summary</h4>
          <p>{report.llm_summary}</p>
        </section>
      )}

      {!healthy && patch && (
        <section className="report-section patch-box">
          <h4><Wrench size={16} /> Proposed fix{patch.file_path && <> for <code>{patch.file_path}</code></>}</h4>
          {patch.status === 'generated' && patch.diff ? (
            <>
              <DiffView diff={patch.diff} />
              <div className="patch-actions">
                {!report.fix_pr_url ? (
                  <button className="submit-btn primary-glow" onClick={handleCreatePr} disabled={creating}>
                    {creating ? <Loader2 size={16} className="spin" /> : <GitPullRequest size={16} />}
                    {creating ? 'Opening pull request...' : 'Create fix pull request'}
                  </button>
                ) : (
                  <div className="pr-status">
                    <a href={report.fix_pr_url} target="_blank" rel="noreferrer" className="inline-link">
                      <GitPullRequest size={16} /> Pull request #{report.fix_pr_number} <ExternalLink size={12} />
                    </a>
                    <VerificationBadge status={report.verification_status} />
                    <button className="btn-secondary" onClick={handleCheckNow}>Check CI now</button>
                  </div>
                )}
              </div>
              {report.verification?.detail && <p className="muted-text">{report.verification.detail}</p>}
            </>
          ) : (
            <p className="muted-text">
              {patch.status === 'rejected' ? 'The generated patch was rejected by validation: ' : 'No patch: '}
              {patch.reason}
            </p>
          )}
          {actionError && <div className="error-alert">{actionError}</div>}
        </section>
      )}

      {report.warnings.length > 0 && (
        <section className="report-section">
          <h4><AlertTriangle size={16} /> Analysis notes</h4>
          <ul className="warning-list">{report.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>
        </section>
      )}

      {report.report_preview && (
        <details className="raw-report">
          <summary>Show the markdown report</summary>
          <div className="code-snippet-box">
            <div className="snippet-header">
              <span>Report posted to pull requests</span>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => {
                  navigator.clipboard.writeText(report.report_preview ?? '');
                  setCopied(true);
                  window.setTimeout(() => setCopied(false), 2000);
                }}
              >
                {copied ? <><CheckCircle size={14} /> Copied</> : <><Copy size={14} /> Copy</>}
              </button>
            </div>
            <pre className="error-terminal">{report.report_preview}</pre>
          </div>
        </details>
      )}
    </div>
  );
};
