import React, { useState } from 'react';
import { postGitHubWebhook } from '../services/api';
import type { UserAuthData } from '../services/authApi';

interface DashboardWorkspaceProps {
  user: UserAuthData;
  onLogout: () => void;
}

export const DashboardWorkspace: React.FC<DashboardWorkspaceProps> = ({ user, onLogout }) => {
  const [activeTab, setActiveTab] = useState<'ingestion' | 'runs'>('ingestion');

  // Real state populated purely from live FastAPI backend webhook responses
  const [ingestedRuns, setIngestedRuns] = useState<any[]>([]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form states for real ingestion
  const [repository, setRepository] = useState('');
  const [workflow, setWorkflow] = useState('CI / CD Build');
  const [branch, setBranch] = useState('main');
  const [commitSha, setCommitSha] = useState('');
  const [logExcerpt, setLogExcerpt] = useState('');
  const [historicalRuns, setHistoricalRuns] = useState('PASS, FAIL, PASS, FAIL, PASS');

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
      setActiveTab('runs');
    } catch (err: any) {
      setError(err.message || 'Failed to submit webhook to backend server');
    } finally {
      setLoading(false);
    }
  };

  const selectedRun = ingestedRuns.length > 0 ? ingestedRuns[0] : null;

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
          className={`dash-tab ${activeTab === 'ingestion' ? 'active' : ''}`}
          onClick={() => setActiveTab('ingestion')}
        >
          📡 Ingest Failure (FastAPI Endpoint)
        </button>
        <button
          className={`dash-tab ${activeTab === 'runs' ? 'active' : ''}`}
          onClick={() => setActiveTab('runs')}
        >
          📊 Ingested Results & Analysis ({ingestedRuns.length})
        </button>
      </div>

      {/* Tab 1: Live Ingestion Form */}
      {activeTab === 'ingestion' && (
        <div className="glass-card trigger-panel">
          <h3>Post Live Webhook Failure to Backend</h3>
          <p className="subtitle">
            This sends a live request to <code>POST /webhooks/github</code>. Backend parses your stack trace, runs failure classification, and calculates flaky test probability.
          </p>

          {error && <div className="error-alert">{error}</div>}

          <form onSubmit={handleIngestWebhook} className="webhook-form">
            <div className="form-row">
              <div className="form-group">
                <label>Repository Name *</label>
                <input
                  type="text"
                  placeholder="e.g. acme/payment-service"
                  value={repository}
                  onChange={(e) => setRepository(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label>Workflow Name *</label>
                <input
                  type="text"
                  placeholder="e.g. CI / CD Build"
                  value={workflow}
                  onChange={(e) => setWorkflow(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Target Branch *</label>
                <input
                  type="text"
                  placeholder="main"
                  value={branch}
                  onChange={(e) => setBranch(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label>Commit SHA</label>
                <input
                  type="text"
                  placeholder="e.g. abc1234"
                  value={commitSha}
                  onChange={(e) => setCommitSha(e.target.value)}
                />
              </div>
            </div>

            <div className="form-group">
              <label>Historical Run History (Comma Separated)</label>
              <input
                type="text"
                placeholder="PASS, FAIL, PASS, FAIL, PASS"
                value={historicalRuns}
                onChange={(e) => setHistoricalRuns(e.target.value)}
              />
              <span className="field-hint">Used by Flaky Test Detector to calculate pass/fail interleaving probability.</span>
            </div>

            <div className="form-group">
              <label>Build Log Excerpt / Stack Trace *</label>
              <textarea
                rows={6}
                placeholder={`Paste actual build failure log or stack trace...
Example:
Traceback (most recent call last):
  File "src/auth/service.py", line 42, in validate_token
    raise AssertionError("Invalid token signature")
FAILED tests/test_auth.py::test_invalid_token`}
                value={logExcerpt}
                onChange={(e) => setLogExcerpt(e.target.value)}
                required
              />
            </div>

            <button type="submit" className="submit-btn primary-glow" disabled={loading}>
              {loading ? 'Processing via Backend APIs...' : 'Send Live Failure Event'}
            </button>
          </form>
        </div>
      )}

      {/* Tab 2: Live Ingested Backend Results */}
      {activeTab === 'runs' && (
        <div className="dashboard-grid">
          <div className="runs-list-panel glass-card">
            <h3>Backend Ingestion Stream</h3>
            <p className="subtitle">Real responses returned from FastAPI services</p>

            {ingestedRuns.length === 0 ? (
              <p className="muted-text" style={{ marginTop: '20px' }}>
                No failure events ingested yet. Switch to the <strong>Ingest Failure</strong> tab and submit a live stack trace!
              </p>
            ) : (
              <div className="runs-scroll-list">
                {ingestedRuns.map((entry, idx) => (
                  <div key={idx} className="run-item-card">
                    <div className="run-card-top">
                      <span className="run-id">{entry.delivery_id || `EVT-${idx + 1}`}</span>
                      <span className="badge-red">{entry.job?.conclusion || 'FAILURE'}</span>
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
                    <strong className="text-cyan">
                      {selectedRun.classification?.category || 'N/A'}
                    </strong>
                  </div>
                  <div className="mini-card">
                    <span className="label">Confidence</span>
                    <strong>
                      {selectedRun.classification
                        ? `${(selectedRun.classification.confidence * 100).toFixed(0)}%`
                        : 'N/A'}
                    </strong>
                  </div>
                  <div className="mini-card">
                    <span className="label">Flaky Result</span>
                    <strong className="text-emerald">
                      {selectedRun.flaky_analysis?.classification || 'N/A'}
                    </strong>
                  </div>
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
    </div>
  );
};
