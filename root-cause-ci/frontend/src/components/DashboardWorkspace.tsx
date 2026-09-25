import React, { useCallback, useEffect, useState } from 'react';
import { BookMarked, History, Loader2, LogOut, RefreshCw, Search, Settings, Zap } from 'lucide-react';
import { fetchAnalysisHistory, fetchRepositories, postGitHubAnalysis, type RepositorySummary } from '../services/api';
import type { UserAuthData } from '../services/authApi';
import type { AnalysisReport } from '../types/analysis';
import { AnalysisReportView } from './AnalysisReportView';

interface DashboardWorkspaceProps {
  user: UserAuthData;
  onLogout: () => void;
  onOpenProfile?: () => void;
}

type Tab = 'repositories' | 'github_analysis' | 'runs';

export const DashboardWorkspace: React.FC<DashboardWorkspaceProps> = ({ user, onLogout, onOpenProfile }) => {
  const [activeTab, setActiveTab] = useState<Tab>('repositories');

  const [history, setHistory] = useState<AnalysisReport[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);

  const [repositories, setRepositories] = useState<RepositorySummary[]>([]);
  const [loadingRepos, setLoadingRepos] = useState(false);
  const [repoError, setRepoError] = useState<string | null>(null);

  const [ghRepo, setGhRepo] = useState('');
  const [ghRunId, setGhRunId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisReport | null>(null);

  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const reports = await fetchAnalysisHistory();
      setHistory(reports);
      setSelectedId((current) => current ?? reports[0]?.report_id ?? null);
    } catch {
      /* history is non-critical; keep the previous list */
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  const loadRepositories = useCallback(async () => {
    setLoadingRepos(true);
    setRepoError(null);
    try {
      const data = await fetchRepositories();
      setRepositories(data.repositories ?? []);
    } catch (e) {
      setRepoError(e instanceof Error ? e.message : 'Failed to load repositories');
    } finally {
      setLoadingRepos(false);
    }
  }, []);

  useEffect(() => {
    loadHistory();
    loadRepositories();
    // Webhook-triggered analyses appear without a manual refresh.
    const timer = window.setInterval(loadHistory, 30000);
    return () => window.clearInterval(timer);
  }, [loadHistory, loadRepositories]);

  // Keep the history list and the current result in sync when a report changes (PR created, verified).
  const updateReport = useCallback((updated: AnalysisReport) => {
    setHistory((prev) => prev.map((r) => (r.report_id === updated.report_id ? updated : r)));
    setResult((prev) => (prev && prev.report_id === updated.report_id ? updated : prev));
  }, []);

  const handleGitHubAnalysis = async (e: React.FormEvent) => {
    e.preventDefault();
    const runId = Number.parseInt(ghRunId.trim(), 10);
    if (!Number.isFinite(runId)) {
      setError('The run ID must be a number, for example 1234567890.');
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await postGitHubAnalysis(ghRepo.trim(), runId);
      if (!response.report_id) {
        setError((response as unknown as { message?: string }).message ?? 'No failed jobs to analyse in this run.');
        return;
      }
      setResult(response);
      setHistory((prev) => [response, ...prev.filter((r) => r.report_id !== response.report_id)]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to analyse the pipeline');
    } finally {
      setLoading(false);
    }
  };

  const selected = history.find((r) => r.report_id === selectedId) ?? null;

  return (
    <div className="dashboard-layout">
      <aside className="dashboard-sidebar">
        <div className="sidebar-user">
          <div className="user-avatar">{user.full_name.charAt(0)}</div>
          <div className="sidebar-user-text">
            <div className="sidebar-user-name">{user.full_name}</div>
            <div className="sidebar-user-email">{user.email}</div>
          </div>
        </div>

        <button className={`sidebar-nav-item ${activeTab === 'repositories' ? 'active' : ''}`} onClick={() => setActiveTab('repositories')}>
          <BookMarked size={18} /> Repositories
        </button>
        <button className={`sidebar-nav-item ${activeTab === 'github_analysis' ? 'active' : ''}`} onClick={() => setActiveTab('github_analysis')}>
          <Search size={18} /> Pipeline Analysis
        </button>
        <button className={`sidebar-nav-item ${activeTab === 'runs' ? 'active' : ''}`} onClick={() => setActiveTab('runs')}>
          <History size={18} /> History ({history.length})
        </button>

        <div style={{ flex: 1 }} />
        <button className="sidebar-nav-item" onClick={onOpenProfile}>
          <Settings size={18} /> Settings
        </button>
        <button className="sidebar-nav-item sidebar-signout" onClick={onLogout}>
          <LogOut size={18} /> Sign Out
        </button>
      </aside>

      <main className="dashboard-content-area">
        {activeTab === 'repositories' && (
          <div className="dashboard-page">
            <div className="page-header">
              <h2><BookMarked size={28} className="text-indigo" /> Repositories</h2>
              <p>Your GitHub repositories with Actions workflows and their latest run.</p>
            </div>
            <div className="glass-card">
              <div className="card-title-row">
                <h3>Connected repositories</h3>
                <button className="btn-secondary" onClick={loadRepositories} disabled={loadingRepos}>
                  <RefreshCw size={14} className={loadingRepos ? 'spin' : ''} /> Refresh
                </button>
              </div>
              {repoError && <div className="error-alert">{repoError}</div>}
              {loadingRepos ? (
                <p className="muted-text">Loading repositories...</p>
              ) : repositories.length === 0 ? (
                <p className="muted-text">No repositories with GitHub Actions were found for your token.</p>
              ) : (
                <div className="repo-grid">
                  {repositories.map((repo) => (
                    <div key={repo.id} className="run-item-card repo-card">
                      <h4>{repo.name}</h4>
                      <p className="muted-text">{repo.full_name}</p>
                      {repo.description && <p className="repo-description">{repo.description}</p>}
                      {repo.latest_run_id && (
                        <p className="repo-run">
                          Latest run #{repo.latest_run_id}:{' '}
                          <strong className={repo.latest_run_conclusion === 'success' ? 'text-emerald'
                            : repo.latest_run_conclusion === 'failure' ? 'text-red' : 'text-cyan'}>
                            {(repo.latest_run_conclusion ?? repo.latest_run_status ?? 'unknown').toUpperCase()}
                          </strong>
                        </p>
                      )}
                      <button
                        className="btn-secondary"
                        disabled={!repo.latest_run_id}
                        onClick={() => {
                          setGhRepo(repo.full_name);
                          if (repo.latest_run_id) setGhRunId(String(repo.latest_run_id));
                          setActiveTab('github_analysis');
                        }}
                      >
                        {repo.latest_run_id ? 'Analyze latest run' : 'No runs yet'}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'github_analysis' && (
          <div className="dashboard-page">
            <div className="page-header">
              <h2><Search size={28} className="text-indigo" /> Pipeline Analysis</h2>
              <p>Diagnose a failed GitHub Actions run, rank the commits that could have caused it and propose a verified fix.</p>
            </div>
            <div className="glass-card trigger-panel">
              {error && <div className="error-alert">{error}</div>}
              <form onSubmit={handleGitHubAnalysis} className="webhook-form">
                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="gh-repo">GitHub repository</label>
                    <input id="gh-repo" type="text" placeholder="owner/repo" value={ghRepo}
                      onChange={(e) => setGhRepo(e.target.value)} required />
                  </div>
                  <div className="form-group">
                    <label htmlFor="gh-run">Workflow run ID</label>
                    <input id="gh-run" type="text" inputMode="numeric" placeholder="1234567890" value={ghRunId}
                      onChange={(e) => setGhRunId(e.target.value)} required />
                  </div>
                </div>
                <button type="submit" className="submit-btn primary-glow" disabled={loading}>
                  {loading ? <><Loader2 size={16} className="spin" /> Collecting evidence...</> : 'Run pipeline analysis'}
                </button>
              </form>
            </div>
            {result && (
              <div className="glass-card run-detail-panel">
                <AnalysisReportView report={result} onUpdate={updateReport} />
              </div>
            )}
          </div>
        )}

        {activeTab === 'runs' && (
          <div className="dashboard-grid">
            <div className="page-header history-header">
              <h2><History size={28} className="text-indigo" /> Analysis history</h2>
              <p>Every analysis you ran, plus failures analysed automatically from GitHub webhooks.</p>
            </div>
            <div className="runs-list-panel glass-card">
              <div className="card-title-row">
                <h3>Reports</h3>
                <button className="btn-secondary" onClick={loadHistory} disabled={historyLoading}>
                  <RefreshCw size={14} className={historyLoading ? 'spin' : ''} /> Refresh
                </button>
              </div>
              {history.length === 0 ? (
                <p className="muted-text">No analyses yet. Run a pipeline analysis to get started.</p>
              ) : (
                <div className="runs-scroll-list">
                  {history.map((entry) => (
                    <button
                      type="button"
                      key={entry.report_id}
                      className={`run-item-card ${selectedId === entry.report_id ? 'active' : ''}`}
                      onClick={() => setSelectedId(entry.report_id)}
                    >
                      <div className="run-card-top">
                        <span className="run-id">Run #{entry.run_id}</span>
                        <span className={entry.is_healthy ? 'badge-green' : 'badge-red'}>
                          {entry.is_healthy ? 'SUCCESS' : 'FAILURE'}
                        </span>
                      </div>
                      <h4 className="repo-title">{entry.repository}</h4>
                      <div className="run-meta">
                        {entry.branch && <span>Branch: <code>{entry.branch}</code></span>}
                        {entry.source === 'webhook' && <span className="auto-tag"><Zap size={12} /> auto</span>}
                        {entry.verification_status && <span className="auto-tag">fix {entry.verification_status}</span>}
                      </div>
                      <div className="category-tag">{entry.classification?.category}</div>
                    </button>
                  ))}
                </div>
              )}
            </div>
            <div className="run-detail-panel glass-card">
              {selected ? (
                <AnalysisReportView report={selected} onUpdate={updateReport} />
              ) : (
                <div className="empty-state"><p className="muted-text">Select a report to view its details.</p></div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
};
