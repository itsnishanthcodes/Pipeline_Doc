import React, { useState, useEffect } from 'react';
import { postGitHubWebhook, postGitHubAnalysis, fetchAnalysisHistory } from '../services/api';
import type { UserAuthData } from '../services/authApi';

interface DashboardWorkspaceProps {
  user: UserAuthData;
  onLogout: () => void;
}

export const DashboardWorkspace: React.FC<DashboardWorkspaceProps> = ({ user, onLogout }) => {
  const [activeTab, setActiveTab] = useState<'github_analysis' | 'runs'>('github_analysis');

  // Real state populated purely from live FastAPI backend webhook responses
  const [ingestedRuns, setIngestedRuns] = useState<any[]>([]);
  const [selectedIndex, setSelectedIndex] = useState<number>(0);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form states for real ingestion
  const [repository, setRepository] = useState('');
  const [workflow, setWorkflow] = useState('CI / CD Build');
  const [branch, setBranch] = useState('main');
  const [commitSha, setCommitSha] = useState('');
  const [logExcerpt, setLogExcerpt] = useState('');
  const [historicalRuns, setHistoricalRuns] = useState('PASS, FAIL, PASS, FAIL, PASS');

  // GitHub Analysis states
  const [ghRepo, setGhRepo] = useState('');
  const [ghRunId, setGhRunId] = useState('');
  const [ghResult, setGhResult] = useState<any>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    fetchAnalysisHistory().then((data) => {
      if (data && data.reports && data.reports.length > 0) {
        const formatted = data.reports.map((r: any) => ({
          delivery_id: `GH-${r.run_id}`,
          event_type: 'github_analysis',
          pipeline_run: {
            repository: r.repository,
            workflow: r.job_name || 'GitHub Action',
            branch: 'main',
          },
          job: {
            conclusion: r.is_healthy || r.classification?.category === 'HEALTHY' ? 'SUCCESS' : 'FAILURE',
          },
          failure: {
            error_message: r.report_preview,
            file_path: 'GitHub Actions Log',
            line_number: 1,
            test_name: r.job_name,
          },
          classification: r.classification,
          llm_summary: r.llm_summary,
          pr_title: r.pr_title,
          pr_number: r.pr_number,
          author: r.author,
        }));
        setIngestedRuns(formatted);
      }
    });
  }, []);

  const handleGitHubAnalysis = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setGhResult(null);

    const cleanRepo = ghRepo.trim();
    const cleanRunId = ghRunId.trim();

    try {
      const response = await postGitHubAnalysis(cleanRepo, parseInt(cleanRunId, 10));
      setGhResult(response);

      // Persist to history stream
      const historyEntry = {
        delivery_id: `GH-${cleanRunId}`,
        event_type: 'github_analysis',
        pipeline_run: {
          repository: cleanRepo,
          workflow: response.job_name || 'GitHub Action',
          branch: 'main',
        },
        job: {
          conclusion: response.is_healthy || response.classification?.category === 'HEALTHY' ? 'SUCCESS' : 'FAILURE',
        },
        failure: {
          error_message: response.report_preview,
          file_path: 'GitHub Actions Log',
          line_number: 1,
          test_name: response.job_name,
        },
        classification: response.classification,
        flaky_analysis: { classification: 'DETERMINISTIC' },
      };
      setIngestedRuns((prev) => [historyEntry, ...prev]);
    } catch (err: any) {
      setError(err.message || 'Failed to trigger GitHub analysis');
    } finally {
      setLoading(false);
    }
  };

  const handleIngestWebhook = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const runsArray = historicalRuns.split(',').map((s) => s.trim().toUpperCase());

    try {
      const response = await postGitHubWebhook({
        repository,
        workflow,
        branch,
        commit_sha: commitSha || 'head',
        log_excerpt: logExcerpt,
        historical_runs: runsArray,
      });

      const result = response.ingestion;
      const newEntry = {
        delivery_id: response.delivery_id,
        event_type: response.event_type,
        pipeline_run: result.pipeline_run,
        job: result.job,
        failure: result.failure,
        classification: result.classification,
        flaky_analysis: result.flaky_analysis,
        error_signatures: result.error_signatures,
      };

      setIngestedRuns((prev) => [newEntry, ...prev]);
      setSelectedIndex(0);
      setActiveTab('runs');
    } catch (err: any) {
      setError(err.message || 'Failed to submit webhook to backend server');
    } finally {
      setLoading(false);
    }
  };

  const selectedRun = ingestedRuns.length > 0 && selectedIndex < ingestedRuns.length ? ingestedRuns[selectedIndex] : null;

  return (
    <div className="dashboard-container">
      {/* Header */}
      <header className="dashboard-header glass-card">
        <div className="user-welcome-group">
          <div className="user-avatar">{user.full_name.charAt(0)}</div>
          <div>
            <h2>Developer CI Workspace</h2>
            <p className="user-email-badge">
              Logged in as: <strong>{user.email}</strong> • Role: <strong>{user.role}</strong>
              {user.github_username && <span className="gh-tag"> • @{user.github_username}</span>}
            </p>
          </div>
        </div>

        <div className="dashboard-actions">
          <button className="btn-secondary" onClick={onLogout}>
            Sign Out
          </button>
        </div>
      </header>

      {/* Tabs */}
      <div className="dashboard-nav-tabs">
        <button
          className={`dash-tab ${activeTab === 'github_analysis' ? 'active' : ''}`}
          onClick={() => setActiveTab('github_analysis')}
        >
          🔍 GitHub Pipeline Analysis
        </button>
        <button
          className={`dash-tab ${activeTab === 'runs' ? 'active' : ''}`}
          onClick={() => setActiveTab('runs')}
        >
          📊 Ingestion History ({ingestedRuns.length})
        </button>
      </div>



      {/* Tab 2: Live Ingested Backend Results */}
      {activeTab === 'runs' && (
        <div className="dashboard-grid">
          <div className="runs-list-panel glass-card">
            <h3>Backend Ingestion Stream</h3>
            <p className="subtitle">Real responses returned from FastAPI services</p>

            {ingestedRuns.length === 0 ? (
              <p className="muted-text" style={{ marginTop: '20px' }}>
                No failure events ingested yet. Run a <strong>GitHub Pipeline Analysis</strong> or submit a live stack trace!
              </p>
            ) : (
              <div className="runs-scroll-list">
                {ingestedRuns.map((entry, idx) => (
                  <div
                    key={idx}
                    className={`run-item-card ${selectedIndex === idx ? 'active' : ''}`}
                    onClick={() => setSelectedIndex(idx)}
                    style={{
                      cursor: 'pointer',
                      borderColor: selectedIndex === idx ? '#818cf8' : undefined,
                      backgroundColor: selectedIndex === idx ? 'rgba(99, 102, 241, 0.15)' : undefined
                    }}
                  >
                    <div className="run-card-top">
                      <span className="run-id">{entry.delivery_id || `EVT-${idx + 1}`}</span>
                      <span className={entry.job?.conclusion === 'SUCCESS' || entry.classification?.category === 'HEALTHY' ? 'badge-green' : 'badge-red'}>
                        {entry.job?.conclusion === 'SUCCESS' || entry.classification?.category === 'HEALTHY' ? 'SUCCESS' : (entry.job?.conclusion || 'FAILURE')}
                      </span>
                    </div>
                    <h4 className="repo-title">{entry.pipeline_run?.repository}</h4>
                    <div className="run-meta">
                      <span>Branch: <code>{entry.pipeline_run?.branch}</code></span>
                    </div>
                    <div className="category-tag">
                      {entry.classification?.category || 'PROCESSED'}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="run-detail-panel glass-card">
            {selectedRun ? (
              <>
                <div className="panel-top">
                  <span className="eyebrow">Real Backend Analysis</span>
                  <h3>{selectedRun.pipeline_run?.repository}</h3>
                  <p className="workflow-name">Workflow: {selectedRun.pipeline_run?.workflow}</p>
                </div>

                <div className="detail-cards-grid">
                  <div className="mini-card">
                    <span className="label">Classification</span>
                    <strong className={selectedRun.classification?.category === 'HEALTHY' ? 'text-emerald' : 'text-cyan'}>
                      {selectedRun.classification?.category === 'HEALTHY' ? '🟢 HEALTHY (PASSED)' : selectedRun.classification?.category || 'N/A'}
                    </strong>
                  </div>
                  <div className="mini-card">
                    <span className="label">Author Attribution</span>
                    <strong className="text-cyan">
                      {selectedRun.author ? `@${selectedRun.author}` : 'N/A'}
                    </strong>
                  </div>
                  {selectedRun.pr_title && (
                    <div className="mini-card">
                      <span className="label">Pull Request</span>
                      <strong className="text-indigo">
                        #{selectedRun.pr_number}: {selectedRun.pr_title}
                      </strong>
                    </div>
                  )}
                </div>

                {selectedRun.failure && (
                  <div className="code-snippet-box">
                    <div className="snippet-header">
                      <span>
                        Extracted File: <code>{selectedRun.failure.file_path || 'N/A'}:{selectedRun.failure.line_number || 0}</code>
                      </span>
                      <span>Test: {selectedRun.failure.test_name || 'N/A'}</span>
                    </div>
                    <pre className="error-terminal">
                      {selectedRun.failure.error_message || 'No error message parsed'}
                    </pre>
                  </div>
                )}
              </>
            ) : (
              <div className="empty-state">
                <p className="muted-text">Submit a failure event in the Ingest Failure tab to see backend output here.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 3: GitHub Pipeline Analysis */}
      {activeTab === 'github_analysis' && (
        <div className="glass-card trigger-panel">
          <h3>Analyze GitHub Pipeline Failure</h3>
          <p className="subtitle">
            Fetch pipeline logs from GitHub, classify the root cause, and optionally post an automated analysis report to the relevant Pull Request.
          </p>

          {error && <div className="error-alert">{error}</div>}

          <form onSubmit={handleGitHubAnalysis} className="webhook-form">
            <div className="form-row">
              <div className="form-group">
                <label>GitHub Repository *</label>
                <input
                  type="text"
                  placeholder="e.g. owner/repo"
                  value={ghRepo}
                  onChange={(e) => setGhRepo(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label>GitHub Run ID *</label>
                <input
                  type="text"
                  placeholder="e.g. 1234567890"
                  value={ghRunId}
                  onChange={(e) => setGhRunId(e.target.value)}
                  required
                />
              </div>
            </div>

            <button type="submit" className="submit-btn primary-glow" disabled={loading}>
              {loading ? 'Analyzing GitHub Pipeline...' : 'Run Pipeline Analysis'}
            </button>
          </form>

          {ghResult && (
            <div className="run-detail-panel glass-card" style={{ marginTop: '20px' }}>
              <div className="panel-top">
                <span className="eyebrow">Analysis Complete</span>
                <h3>Job: {ghResult.job_name}</h3>
                <p className="workflow-name">Status: {ghResult.message || 'Processed'}</p>
              </div>

              {ghResult.classification && (
                <div className="detail-cards-grid">
                  <div className="mini-card">
                    <span className="label">Category</span>
                    <strong className={ghResult.classification.category === 'HEALTHY' ? 'text-emerald' : 'text-cyan'}>
                      {ghResult.classification.category === 'HEALTHY' ? '🟢 HEALTHY (PASSED)' : ghResult.classification.category}
                    </strong>
                  </div>
                  <div className="mini-card">
                    <span className="label">Comment Posted to PR</span>
                    <strong className={ghResult.comment_posted ? 'text-emerald' : 'text-red'}>
                      {ghResult.comment_posted ? 'YES' : 'NO'}
                    </strong>
                  </div>
                  {ghResult.author && (
                    <div className="mini-card">
                      <span className="label">Author Attribution</span>
                      <strong className="text-cyan">@{ghResult.author}</strong>
                    </div>
                  )}
                </div>
              )}

              {ghResult.llm_summary && (
                <div className="mini-card" style={{ marginTop: '15px', background: 'rgba(99, 102, 241, 0.1)', borderColor: 'rgba(99, 102, 241, 0.3)' }}>
                  <span className="label" style={{ color: '#818cf8', fontWeight: 600 }}>🤖 Groq LLM Narrative Summary</span>
                  <p style={{ marginTop: '8px', fontSize: '0.95rem', lineHeight: '1.5' }}>
                    {ghResult.llm_summary}
                  </p>
                </div>
              )}

              {ghResult.report_preview && (
                <div className="code-snippet-box">
                  <div className="snippet-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span>Generated Report Preview</span>
                    <button
                      type="button"
                      className="btn-secondary"
                      style={{ padding: '4px 10px', fontSize: '0.8rem' }}
                      onClick={() => {
                        navigator.clipboard.writeText(ghResult.report_preview);
                        setCopied(true);
                        setTimeout(() => setCopied(false), 2000);
                      }}
                    >
                      {copied ? '✅ Copied to Clipboard!' : '📋 Copy Report'}
                    </button>
                  </div>
                  <pre className="error-terminal">
                    {ghResult.report_preview}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
