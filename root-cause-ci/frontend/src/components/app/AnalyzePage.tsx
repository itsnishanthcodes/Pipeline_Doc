import { CircleAlert, ExternalLink, LoaderCircle, RefreshCw } from 'lucide-react';
import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '../../lib/api';
import { useAuth } from '../../lib/auth';
import { runLabel, runTone, shortSha, timeAgo } from '../../lib/format';
import { useToast } from '../../lib/toast';
import type { Repository, WorkflowRun } from '../../types/api';
import { PageHeader } from './AppShell';

export function AnalyzePage() {
  const { user } = useAuth();
  const notify = useToast();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const repo = params.get('repo') ?? '';

  const [repos, setRepos] = useState<Repository[]>([]);
  const [runs, setRuns] = useState<WorkflowRun[] | null>(null);
  const [runsError, setRunsError] = useState<string | null>(null);
  const [loadingRuns, setLoadingRuns] = useState(false);
  const [analyzing, setAnalyzing] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [manualRepo, setManualRepo] = useState('');
  const [manualRun, setManualRun] = useState('');

  useEffect(() => {
    if (user?.has_github_token) api.repositories().then((d) => setRepos(d.repositories)).catch(() => setRepos([]));
  }, [user?.has_github_token]);

  const loadRuns = useCallback(async (fullName: string) => {
    if (!fullName) return;
    setLoadingRuns(true);
    setRunsError(null);
    try {
      setRuns((await api.runs(fullName)).runs);
    } catch (e) {
      setRunsError(e instanceof Error ? e.message : 'Runs could not be loaded.');
      setRuns([]);
    } finally {
      setLoadingRuns(false);
    }
  }, []);

  useEffect(() => {
    setRuns(null);
    if (repo) loadRuns(repo);
  }, [repo, loadRuns]);

  const analyze = async (repository: string, runId: number) => {
    setAnalyzing(runId);
    setError(null);
    try {
      const report = await api.analyze(repository, runId);
      if (!report.report_id) {
        setError(report.message ?? 'This run has no failed jobs to diagnose.');
        return;
      }
      notify(report.is_healthy ? `Run #${runId} passed, so there is nothing to fix.` : `Diagnosis ready for run #${runId}.`);
      navigate(`/app/reports/${report.report_id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'The run could not be analysed.');
    } finally {
      setAnalyzing(null);
    }
  };

  const submitManual = (e: FormEvent) => {
    e.preventDefault();
    const id = Number.parseInt(manualRun.trim(), 10);
    if (!/^[\w.-]+\/[\w.-]+$/.test(manualRepo.trim())) return setError('Enter the repository as owner/name, for example acme/checkout.');
    if (!Number.isFinite(id) || id <= 0) return setError('The run ID is the number at the end of the run URL on GitHub.');
    analyze(manualRepo.trim(), id);
  };

  return (
    <div className="page">
      <PageHeader
        title="Analyze a run"
        description="Pick a failed workflow run. The diagnosis reads its logs, the job's history and every commit since the last passing run."
      />

      {error && <div className="notice notice-error" role="alert"><CircleAlert size={16} /><span>{error}</span></div>}
      {analyzing && (
        <div className="notice" role="status">
          <LoaderCircle size={16} className="spin" />
          <span>Diagnosing run #{analyzing}. This collects logs, run history and commits from GitHub and can take up to a minute.</span>
        </div>
      )}

      <div className="analyze-grid">
        <section className="list-panel glass" aria-labelledby="runs-title">
          <div className="list-toolbar">
            <label htmlFor="repo-select" className="sr-only">Repository</label>
            <select id="repo-select" className="select" value={repo}
                    onChange={(e) => setParams(e.target.value ? { repo: e.target.value } : {})}>
              <option value="">Choose a repository</option>
              {repo && !repos.some((r) => r.full_name === repo) && <option value={repo}>{repo}</option>}
              {repos.map((r) => <option key={r.id} value={r.full_name}>{r.full_name}</option>)}
            </select>
            {repo && (
              <button type="button" className="icon-btn" onClick={() => loadRuns(repo)} aria-label="Reload runs">
                <RefreshCw size={15} className={loadingRuns ? 'spin' : ''} />
              </button>
            )}
          </div>
          <h2 id="runs-title" className="sr-only">Recent runs</h2>

          {!repo && (
            <p className="list-empty muted">
              {user?.has_github_token
                ? 'Choose a repository to see its recent workflow runs.'
                : <>Connect a GitHub token in <Link to="/app/settings">Settings</Link> to list repositories, or enter a run below.</>}
            </p>
          )}
          {runsError && <p className="list-empty text-fail">{runsError}</p>}
          {repo && runs === null && !runsError && (
            <div className="rows">{[0, 1, 2].map((i) => <div key={i} className="row"><span className="skeleton" style={{ height: 20, width: '70%' }} /></div>)}</div>
          )}
          {runs && runs.length === 0 && !runsError && <p className="list-empty muted">This repository has no workflow runs yet.</p>}
          {runs && runs.length > 0 && (
            <ul className="rows">
              {runs.map((run) => {
                const tone = runTone(run.status, run.conclusion);
                const done = run.status === 'completed';
                return (
                  <li key={run.id} className="row run-row">
                    <span className={`status status-${tone}`}>{runLabel(run.status, run.conclusion)}</span>
                    <div className="run-main">
                      <strong>{run.commit_message || `${run.name} #${run.run_number}`}</strong>
                      <span className="faint small run-meta">
                        <span>{run.name} #{run.run_number}</span>
                        {run.branch && <code>{run.branch}</code>}
                        {run.head_sha && <span className="mono">{shortSha(run.head_sha)}</span>}
                        {run.actor && <span>by {run.actor}</span>}
                        <span>{timeAgo(run.created_at)}</span>
                      </span>
                    </div>
                    <div className="run-actions">
                      {run.html_url && (
                        <a className="icon-btn" href={run.html_url} target="_blank" rel="noreferrer" aria-label={`Open run ${run.run_number} on GitHub`}>
                          <ExternalLink size={15} />
                        </a>
                      )}
                      <button type="button" className={`btn btn-sm ${tone === 'fail' ? 'btn-primary' : ''}`}
                              disabled={!done || analyzing !== null} onClick={() => analyze(repo, run.id)}
                              title={done ? undefined : 'Wait for the run to finish'}>
                        {analyzing === run.id && <LoaderCircle size={14} className="spin" />}
                        {tone === 'fail' ? 'Diagnose' : 'Check'}
                      </button>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        <aside className="side-panel glass">
          <h2 className="panel-title">Have a run link?</h2>
          <p className="muted small">
            Paste the repository and the run ID from a URL such as github.com/acme/checkout/actions/runs/<strong>1234567890</strong>.
          </p>
          <form className="stack" onSubmit={submitManual}>
            <div className="field">
              <label htmlFor="m-repo">Repository</label>
              <input id="m-repo" className="input" placeholder="owner/name" value={manualRepo}
                     onChange={(e) => setManualRepo(e.target.value)} spellCheck={false} />
            </div>
            <div className="field">
              <label htmlFor="m-run">Run ID</label>
              <input id="m-run" className="input" inputMode="numeric" value={manualRun}
                     onChange={(e) => setManualRun(e.target.value)} />
            </div>
            <button type="submit" className="btn" disabled={analyzing !== null}>Diagnose this run</button>
          </form>
        </aside>
      </div>
    </div>
  );
}
