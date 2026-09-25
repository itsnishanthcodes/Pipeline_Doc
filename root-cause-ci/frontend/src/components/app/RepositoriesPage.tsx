import { CircleAlert, ExternalLink, Lock, RefreshCw } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../../lib/api';
import { useAuth } from '../../lib/auth';
import { runLabel, runTone, timeAgo } from '../../lib/format';
import type { Repository } from '../../types/api';
import { PageHeader } from './AppShell';

export function RepositoriesPage() {
  const { user } = useAuth();
  const [repos, setRepos] = useState<Repository[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setRepos((await api.repositories()).repositories);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Repositories could not be loaded.');
      setRepos([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user?.has_github_token) load();
  }, [user?.has_github_token, load]);

  const visible = useMemo(
    () => (repos ?? []).filter((r) => r.full_name.toLowerCase().includes(query.trim().toLowerCase())),
    [repos, query],
  );
  const failing = (repos ?? []).filter((r) => runTone(r.latest_run_status, r.latest_run_conclusion) === 'fail').length;

  if (!user?.has_github_token) {
    return (
      <div className="page">
        <PageHeader title="Repositories" />
        <div className="empty glass">
          <h2>Connect GitHub to see your repositories</h2>
          <p className="muted">
            Root Cause CI reads workflow runs and logs with a personal access token. Add one in Settings and your
            repositories with GitHub Actions will show up here.
          </p>
          <Link to="/app/settings" className="btn btn-primary">Connect GitHub</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <PageHeader
        title="Repositories"
        description={repos && repos.length > 0
          ? `${repos.length} repositories run GitHub Actions${failing ? `, and ${failing} ${failing === 1 ? 'is' : 'are'} failing right now` : ''}.`
          : 'Repositories your token can see that run GitHub Actions.'}
        actions={(
          <button type="button" className="btn" onClick={load} disabled={loading}>
            <RefreshCw size={15} className={loading ? 'spin' : ''} /> Refresh
          </button>
        )}
      />

      {error && <div className="notice notice-error" role="alert"><CircleAlert size={16} /><span>{error}</span></div>}

      <div className="list-panel glass">
        <div className="list-toolbar">
          <input className="input" type="search" placeholder="Filter repositories" value={query}
                 onChange={(e) => setQuery(e.target.value)} aria-label="Filter repositories" />
        </div>
        {repos === null || (loading && repos.length === 0) ? (
          <div className="rows">{[0, 1, 2, 3].map((i) => <div key={i} className="row"><span className="skeleton" style={{ height: 20, width: '60%' }} /></div>)}</div>
        ) : visible.length === 0 ? (
          <p className="list-empty muted">
            {repos.length === 0 ? 'None of the repositories your token can see run GitHub Actions yet.' : 'No repositories match that filter.'}
          </p>
        ) : (
          <ul className="rows">
            {visible.map((repo) => {
              const tone = runTone(repo.latest_run_status, repo.latest_run_conclusion);
              return (
                <li key={repo.id} className="row repo-row">
                  <div className="repo-main">
                    <div className="repo-name">
                      <a href={repo.html_url} target="_blank" rel="noreferrer">{repo.full_name}</a>
                      {repo.private && <Lock size={13} className="faint" aria-label="Private" />}
                    </div>
                    {repo.description && <p className="muted small repo-desc">{repo.description}</p>}
                  </div>
                  <div className="repo-run">
                    {repo.latest_run_id ? (
                      <>
                        <span className={`status status-${tone}`}>{runLabel(repo.latest_run_status, repo.latest_run_conclusion)}</span>
                        <span className="faint small">{repo.latest_run_name} {timeAgo(repo.latest_run_at)}</span>
                      </>
                    ) : <span className="faint small">No runs yet</span>}
                  </div>
                  <div className="repo-actions">
                    <Link to={`/app/analyze?repo=${encodeURIComponent(repo.full_name)}`}
                          className={`btn btn-sm ${tone === 'fail' ? 'btn-primary' : ''}`}>
                      {tone === 'fail' ? 'Diagnose failure' : 'View runs'}
                    </Link>
                    <a className="icon-btn" href={repo.html_url + '/actions'} target="_blank" rel="noreferrer"
                       aria-label={`Open ${repo.full_name} Actions on GitHub`}>
                      <ExternalLink size={15} />
                    </a>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
