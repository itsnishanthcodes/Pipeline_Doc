import { Check, CircleAlert, CircleCheck, ExternalLink, GitPullRequest, LoaderCircle, RefreshCw } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { api } from '../../lib/api';
import { categoryLabel, flakyLabel, percent, shortSha, timeAgo } from '../../lib/format';
import { useToast } from '../../lib/toast';
import type { AnalysisReport, CandidateCommit } from '../../types/analysis';
import { DiffView } from './DiffView';

const SIGNAL_NAMES: Record<string, string> = {
  temporal_proximity: 'Timing',
  file_overlap: 'Files',
  stack_trace_overlap: 'Stack trace',
  function_overlap: 'Functions',
  dependency_relationship: 'Imports',
  historical_evidence: 'History',
};

function CommitRow({ commit, rank, open, onToggle }: {
  commit: CandidateCommit; rank: number; open: boolean; onToggle: () => void;
}) {
  const reasons = Object.entries(commit.reasons ?? {}).filter(([k]) => (commit.signals[k] ?? 0) > 0);
  return (
    <li className={`commit ${rank === 1 ? 'is-top' : ''}`}>
      <button type="button" className="commit-summary" aria-expanded={open} onClick={onToggle}>
        <span className="commit-rank" aria-hidden="true">{rank}</span>
        <span className="commit-text">
          <span className="commit-title">
            <span className="mono commit-sha">{shortSha(commit.commit_sha)}</span>
            <span>{commit.message || 'No commit message'}</span>
          </span>
          <span className="faint small">{commit.author ? `by ${commit.author}` : 'author unknown'}</span>
        </span>
        <span className="commit-score">
          <span className="meter" aria-hidden="true"><span style={{ width: percent(commit.confidence_score) }} /></span>
          <span className="small">{percent(commit.confidence_score)}</span>
        </span>
      </button>
      {open && (
        <div className="commit-detail">
          {reasons.length > 0 ? (
            <ul className="reason-list">
              {reasons.map(([key, text]) => (
                <li key={key}><span className="reason-name">{SIGNAL_NAMES[key] ?? key}</span><span>{text}</span></li>
              ))}
            </ul>
          ) : <p className="faint small">No evidence links this commit to the failure.</p>}
          {commit.changed_files.length > 0 && (
            <p className="faint small commit-files">
              Changed {commit.changed_files.slice(0, 6).map((f) => <code key={f}>{f}</code>)}
              {commit.changed_files.length > 6 && ` and ${commit.changed_files.length - 6} more`}
            </p>
          )}
        </div>
      )}
    </li>
  );
}

function FixTracker({ report }: { report: AnalysisReport }) {
  const v = report.verification_status;
  const steps = [
    { label: 'Patch validated', done: true },
    { label: 'Pull request opened', done: Boolean(report.fix_pr_url) },
    { label: 'CI running on the fix', done: v === 'verified' || v === 'failed', active: v === 'pending' || v === 'running' },
    { label: v === 'failed' ? 'CI failed on the fix' : 'Verified by CI', done: v === 'verified', failed: v === 'failed' },
  ];
  return (
    <ol className="tracker" aria-label="Fix progress">
      {steps.map((s) => (
        <li key={s.label} className={`${s.done ? 'is-done' : ''} ${s.active ? 'is-active' : ''} ${s.failed ? 'is-failed' : ''}`}>
          <span className="tracker-dot" aria-hidden="true">
            {s.failed ? <CircleAlert size={14} /> : s.done ? <Check size={13} strokeWidth={3} /> : s.active ? <LoaderCircle size={13} className="spin" /> : null}
          </span>
          <span>{s.label}</span>
        </li>
      ))}
    </ol>
  );
}

export function ReportView({ report, onChange }: { report: AnalysisReport; onChange: (r: AnalysisReport) => void }) {
  const notify = useToast();
  const [openCommit, setOpenCommit] = useState<string | null>(report.candidates?.[0]?.commit_sha ?? null);
  const [creating, setCreating] = useState(false);
  const [checking, setChecking] = useState(false);
  const polls = useRef(0);

  // Watch CI on the fix branch until it is verified or fails (about 10 minutes at most).
  useEffect(() => {
    const status = report.verification_status;
    if (!report.fix_branch || (status !== 'pending' && status !== 'running')) return;
    polls.current = 0;
    const timer = window.setInterval(async () => {
      polls.current += 1;
      if (polls.current > 40) return window.clearInterval(timer);
      try {
        const updated = await api.checkVerification(report.report_id);
        onChange(updated);
        if (updated.verification_status === 'verified') notify('The fix passed CI.');
        if (updated.verification_status === 'failed') notify('The fix failed CI on its branch.', 'error');
      } catch {
        /* transient GitHub errors: keep watching */
      }
    }, 15000);
    return () => window.clearInterval(timer);
  }, [report.report_id, report.fix_branch, report.verification_status, onChange, notify]);

  const createPr = async () => {
    setCreating(true);
    try {
      const updated = await api.createFixPullRequest(report.report_id);
      onChange(updated);
      notify(`Opened pull request #${updated.fix_pr_number}. Watching CI on the fix branch.`);
    } catch (e) {
      notify(e instanceof Error ? e.message : 'The pull request could not be opened.', 'error');
    } finally {
      setCreating(false);
    }
  };

  const checkNow = async () => {
    setChecking(true);
    try {
      onChange(await api.checkVerification(report.report_id));
    } catch (e) {
      notify(e instanceof Error ? e.message : 'CI status could not be checked.', 'error');
    } finally {
      setChecking(false);
    }
  };

  const run = report.run;
  const header = (
    <header className="report-header">
      <div>
        <h1>{report.repository}</h1>
        <p className="report-meta muted">
          <span>Run #{report.run_id}{run?.workflow ? ` of ${run.workflow}` : ''}</span>
          {report.branch && <code>{report.branch}</code>}
          {run?.head_sha && <span className="mono">{shortSha(run.head_sha)}</span>}
          <span>{report.source === 'webhook' ? 'Analysed automatically' : 'Analysed'} {timeAgo(report.created_at)}</span>
        </p>
      </div>
      {run?.url && (
        <a className="btn" href={run.url} target="_blank" rel="noreferrer">
          Open run on GitHub <ExternalLink size={15} />
        </a>
      )}
    </header>
  );

  if (report.is_healthy) {
    return (
      <div className="report">
        {header}
        <div className="healthy glass">
          <CircleCheck size={28} className="text-pass" />
          <div>
            <h2>This run passed</h2>
            <p className="muted">Every job in run #{report.run_id} completed successfully, so there is nothing to diagnose.</p>
          </div>
        </div>
      </div>
    );
  }

  const primary = report.jobs.find((j) => j.name === report.primary_job) ?? report.jobs[0];
  const culprit = report.candidates?.[0];
  const flaky = report.flaky;
  const patch = report.patch;

  return (
    <div className="report">
      {header}

      <section className="verdict glass" aria-label="Diagnosis">
        <div className="verdict-cell">
          <span className="verdict-label">What failed</span>
          <strong className="verdict-value">{categoryLabel(report.classification.category)}</strong>
          {primary?.error_message && <code className="verdict-error">{primary.error_message}</code>}
        </div>
        <div className="verdict-cell">
          <span className="verdict-label">Most likely cause</span>
          {culprit ? (
            <>
              <strong className="verdict-value"><span className="mono text-accent">{shortSha(culprit.commit_sha)}</span></strong>
              <span className="small verdict-sub">{culprit.message}{culprit.author ? `, by ${culprit.author}` : ''}</span>
            </>
          ) : <strong className="verdict-value">Not identified</strong>}
        </div>
        <div className="verdict-cell">
          <span className="verdict-label">Confidence</span>
          <strong className="verdict-value verdict-number">{percent(report.confidence_score)}</strong>
          <span className="meter meter-wide" aria-hidden="true"><span style={{ width: percent(report.confidence_score) }} /></span>
        </div>
        <div className="verdict-cell">
          <span className="verdict-label">Flaky test?</span>
          <strong className={`verdict-value ${flaky?.classification === 'LIKELY_FLAKY' ? 'text-pending' : ''}`}>{flakyLabel(flaky?.classification)}</strong>
          <span className="small verdict-sub">
            {flaky?.same_commit_passed
              ? 'The same commit passed in another run.'
              : `Based on ${flaky?.runs_considered ?? 0} earlier ${flaky?.runs_considered === 1 ? 'run' : 'runs'} of this job.`}
          </span>
        </div>
      </section>

      {report.llm_summary && <p className="report-summary">{report.llm_summary}</p>}

      <div className="report-grid">
        <div className="report-col">
          {report.candidates.length > 0 && (
            <section className="panel glass" aria-labelledby="commits-title">
              <div className="panel-head">
                <h2 id="commits-title" className="panel-title">Commits since the last passing run</h2>
                <span className="faint small">{report.candidates.length} ranked</span>
              </div>
              <ol className="commit-list">
                {report.candidates.map((c, i) => (
                  <CommitRow key={c.commit_sha} commit={c} rank={i + 1} open={openCommit === c.commit_sha}
                             onToggle={() => setOpenCommit(openCommit === c.commit_sha ? null : c.commit_sha)} />
                ))}
              </ol>
            </section>
          )}
        </div>

        <div className="report-col">
          <section className="panel glass" aria-labelledby="jobs-title">
            <h2 id="jobs-title" className="panel-title">Failed {report.jobs.length === 1 ? 'job' : `jobs (${report.jobs.length})`}</h2>
            {report.jobs.map((job) => (
              <div key={job.id} className="job">
                <div className="job-head">
                  <strong>{job.name}</strong>
                  {job.failed_step && <span className="faint small">at step "{job.failed_step}"</span>}
                  {job.html_url && (
                    <a className="inline-link small" href={job.html_url} target="_blank" rel="noreferrer">
                      Log <ExternalLink size={12} />
                    </a>
                  )}
                </div>
                {job.failed_tests.length > 0 && (
                  <div className="job-facts"><span className="faint small">Failing tests</span>{job.failed_tests.slice(0, 4).map((t) => <code key={t}>{t}</code>)}</div>
                )}
                {job.frames.length > 0 && (
                  <div className="job-facts"><span className="faint small">Points to</span>{job.frames.slice(0, 4).map((f) => (
                    <code key={`${f.file}:${f.line}`}>{f.file}:{f.line}</code>
                  ))}</div>
                )}
                {job.key_lines.length > 0 && (
                  <details className="job-log">
                    <summary className="small">Key log lines</summary>
                    <pre>{job.key_lines.slice(-12).join('\n')}</pre>
                  </details>
                )}
                {!job.log_available && <p className="faint small">GitHub did not return logs for this job.</p>}
              </div>
            ))}
          </section>

          {flaky && flaky.historical_runs.length > 1 && (
            <section className="panel glass" aria-labelledby="history-title">
              <h2 id="history-title" className="panel-title">This job on {report.branch ?? 'the branch'}</h2>
              <div className="run-strip" aria-label={`Oldest to newest: ${flaky.historical_runs.join(', ')}`}>
                {flaky.historical_runs.map((o, i) => (
                  <span key={i} className={`run-tick ${o === 'PASS' ? 'is-pass' : 'is-fail'} ${i === flaky.historical_runs.length - 1 ? 'is-current' : ''}`} />
                ))}
              </div>
              <p className="faint small">Oldest on the left. The last mark is this run.</p>
            </section>
          )}
        </div>
      </div>

      {patch && (
        <section className="panel glass fix" aria-labelledby="fix-title">
          <div className="panel-head">
            <h2 id="fix-title" className="panel-title">Proposed fix</h2>
            {patch.status === 'generated' && <FixTracker report={report} />}
          </div>
          {patch.status === 'generated' && patch.diff && patch.file_path ? (
            <>
              <DiffView diff={patch.diff} file={patch.file_path} />
              <div className="fix-actions">
                {report.fix_pr_url ? (
                  <>
                    <a className="btn" href={report.fix_pr_url} target="_blank" rel="noreferrer">
                      <GitPullRequest size={16} /> Pull request #{report.fix_pr_number} <ExternalLink size={14} />
                    </a>
                    <button type="button" className="btn btn-quiet" onClick={checkNow} disabled={checking}>
                      <RefreshCw size={15} className={checking ? 'spin' : ''} /> Check CI now
                    </button>
                    {report.verification?.detail && <span className="faint small">{report.verification.detail}</span>}
                  </>
                ) : (
                  <>
                    <span className="faint small">The pull request only changes {patch.file_path}. It is marked verified when your CI passes on it.</span>
                    <button type="button" className="btn btn-primary" onClick={createPr} disabled={creating}>
                      {creating ? <LoaderCircle size={16} className="spin" /> : <GitPullRequest size={16} />}
                      Open fix pull request
                    </button>
                  </>
                )}
              </div>
            </>
          ) : (
            <div className="notice">
              <CircleAlert size={16} />
              <span>
                {patch.status === 'rejected' ? 'A fix was generated but rejected by validation. ' : 'No fix was proposed. '}
                {patch.reason}
              </span>
            </div>
          )}
        </section>
      )}

      {report.warnings.length > 0 && (
        <section className="panel glass" aria-labelledby="notes-title">
          <h2 id="notes-title" className="panel-title">Notes from this analysis</h2>
          <ul className="notes">{report.warnings.map((w) => <li key={w} className="muted small">{w}</li>)}</ul>
        </section>
      )}

      {report.report_preview && (
        <details className="panel glass raw">
          <summary>Report posted to the pull request</summary>
          <pre>{report.report_preview}</pre>
        </details>
      )}
    </div>
  );
}
