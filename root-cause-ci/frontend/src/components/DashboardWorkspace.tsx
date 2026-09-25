import React, { useState, useEffect } from 'react';
import { BookMarked, Search, History, LogOut, Settings, GitPullRequest, CheckCircle, Copy, Terminal, Wrench } from 'lucide-react';
import { postGitHubWebhook, postGitHubAnalysis, fetchAnalysisHistory, fetchRepositories, fetchRcaEvaluation } from '../services/api';
import type { UserAuthData } from '../services/authApi';

interface DashboardWorkspaceProps {
  user: UserAuthData;
  onLogout: () => void;
  onOpenProfile?: () => void;
}

type AnalysisStageStatus = 'PASSED' | 'FAILED' | 'SKIPPED';

interface AnalysisStage {
  name: string;
  status: AnalysisStageStatus;
  detail: string;
}

function getAnalysisStages(result: any): AnalysisStage[] {
  const authoritative = result.authoritative_rca;
  const hasFailure = Boolean(result.classification && result.classification.category !== 'HEALTHY');
  const flaky = result.flaky_analysis;
  const git = result.git_analysis;
  const evidence = Array.isArray(authoritative?.evidence)
    ? authoritative.evidence
    : (Array.isArray(result.evidence_chain) ? result.evidence_chain : []);
  const localization = result.localization;
  const ast = Array.isArray(result.ast_analysis) ? result.ast_analysis : [];
  const dependencyPaths = Array.isArray(authoritative?.dependency_path) && authoritative.dependency_path.length > 0
    ? [authoritative.dependency_path]
    : (Array.isArray(result.dependency_paths) ? result.dependency_paths : []);

  return [
    { name: 'Log ingestion', status: 'PASSED', detail: 'Workflow run and failed job data were retrieved.' },
    { name: 'Classification', status: result.classification ? 'PASSED' : 'FAILED', detail: result.classification?.category || 'No classification returned.' },
    {
      name: 'Failure localization',
      status: localization?.frames?.length ? 'PASSED' : 'SKIPPED',
      detail: localization?.frames?.length ? `${localization.frames.length} stack frame(s)` : localization?.reason || 'No usable stack trace.',
    },
    {
      name: 'Flaky-test check',
      status: flaky ? 'PASSED' : 'SKIPPED',
      detail: flaky ? flaky.classification : 'No failing test was identified.',
    },
    {
      name: 'Git analysis',
      status: git ? 'PASSED' : hasFailure ? 'SKIPPED' : 'SKIPPED',
      detail: git ? `${git.candidates?.length || 0} candidate commit(s)` : 'Local repository evidence was not supplied.',
    },
    { name: 'AST analysis', status: ast.length > 0 ? 'PASSED' : 'SKIPPED', detail: ast.length > 0 ? `${ast.length} localized file(s)` : 'No localized source file was analyzed.' },
    { name: 'Dependency graph', status: dependencyPaths.length > 0 ? 'PASSED' : 'SKIPPED', detail: dependencyPaths.length > 0 ? `${dependencyPaths.length} path(s)` : 'No verified dependency path was found.' },
    {
      name: 'Root-cause attribution',
      status: authoritative?.status === 'SUPPORTED' || authoritative?.status === 'PARTIAL' ? 'PASSED' : 'SKIPPED',
      detail: authoritative ? `${(authoritative.confidence * 100).toFixed(1)}% confidence (${authoritative.status})` : 'No authoritative RCA returned.',
    },
    { name: 'Evidence chain', status: evidence.length > 0 ? 'PASSED' : 'SKIPPED', detail: `${evidence.length} supporting item(s)` },
    { name: 'Patch generation', status: result.patch_code ? 'PASSED' : 'SKIPPED', detail: result.patch_code ? 'Unified diff returned.' : 'No verified patch generated.' },
    { name: 'Scope validation', status: 'SKIPPED', detail: 'Runs only after a patch verification request.' },
    { name: 'Sandbox verification', status: 'SKIPPED', detail: 'Docker verification is not connected to this analysis path.' },
    { name: 'Fix PR', status: 'SKIPPED', detail: 'A PR is never created before verification passes.' },
  ];
}

export const DashboardWorkspace: React.FC<DashboardWorkspaceProps> = ({ user, onLogout, onOpenProfile }) => {
  const [activeTab, setActiveTab] = useState<'github_analysis' | 'runs' | 'repositories'>('repositories');

  const [ingestedRuns, setIngestedRuns] = useState<any[]>([]);
  const [selectedIndex, setSelectedIndex] = useState<number>(0);
  
  const [repositories, setRepositories] = useState<any[]>([]);
  const [loadingRepos, setLoadingRepos] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [ghRepo, setGhRepo] = useState('');
  const [ghRunId, setGhRunId] = useState('');
  const [ghResult, setGhResult] = useState<any>(null);
  const [copied, setCopied] = useState(false);
  const [evaluation, setEvaluation] = useState<any>(null);

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

    setLoadingRepos(true);
    fetchRepositories().then((data) => {
      if (data && data.repositories) {
        setRepositories(data.repositories);
      }
    }).catch(console.error).finally(() => setLoadingRepos(false));
    fetchRcaEvaluation().then(setEvaluation).catch(() => setEvaluation(null));
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

  const selectedRun = ingestedRuns.length > 0 && selectedIndex < ingestedRuns.length ? ingestedRuns[selectedIndex] : null;

  return (
    <div className="dashboard-layout">
      <aside className="dashboard-sidebar">
        <div style={{ padding: '0 16px 20px', display: 'flex', alignItems: 'center', gap: '12px', borderBottom: '1px solid var(--border-glass)', marginBottom: '10px' }}>
          <div className="user-avatar" style={{ width: '40px', height: '40px', fontSize: '1.2rem', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{user.full_name.charAt(0)}</div>
          <div style={{ overflow: 'hidden' }}>
            <div style={{ fontWeight: 600, color: 'var(--text-main)', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>{user.full_name}</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>{user.email}</div>
          </div>
        </div>

        <button className={`sidebar-nav-item ${activeTab === 'repositories' ? 'active' : ''}`} onClick={() => setActiveTab('repositories')}>
          <BookMarked size={18} />
          Repositories
        </button>
        <button className={`sidebar-nav-item ${activeTab === 'github_analysis' ? 'active' : ''}`} onClick={() => setActiveTab('github_analysis')}>
          <Search size={18} />
          Pipeline Analysis
        </button>
        <button className={`sidebar-nav-item ${activeTab === 'runs' ? 'active' : ''}`} onClick={() => setActiveTab('runs')}>
          <History size={18} />
          History ({ingestedRuns.length})
        </button>

        <div style={{ flex: 1 }} />
        <button className="sidebar-nav-item" onClick={onOpenProfile}>
          <Settings size={18} />
          Settings
        </button>
        <button className="sidebar-nav-item" onClick={onLogout} style={{ color: 'var(--accent-red)' }}>
          <LogOut size={18} />
          Sign Out
        </button>
      </aside>

      <main className="dashboard-content-area">
        {activeTab === 'repositories' && (
          <div className="dashboard-grid" style={{ gridTemplateColumns: '1fr', padding: '0 20px' }}>
            <div className="page-header">
              <h2><BookMarked size={28} style={{ color: 'var(--accent-indigo)' }}/> Repositories</h2>
              <p>Manage and analyze your connected GitHub repositories with active workflows.</p>
            </div>
            {evaluation?.baselines && (
              <div className="glass-card rca-evaluation-panel">
                <div className="page-header compact">
                  <h3>RCA evaluation</h3>
                  <p>Experimental comparison over the persisted controlled benchmark.</p>
                </div>
                <div className="evaluation-table-wrap">
                  <table className="evaluation-table">
                    <thead><tr><th>Configuration</th><th>Top-1</th><th>Top-3</th><th>Evidence</th><th>Cases</th><th>Partial</th><th>Insufficient</th><th>Incorrect</th><th>Avg files</th><th>Avg functions</th><th>Avg nodes</th><th>Avg time</th></tr></thead>
                    <tbody>{Object.entries(evaluation.baselines).map(([name, metrics]: [string, any]) => (
                      <tr key={name}><td>{name.replaceAll('_', ' + ')}</td><td>{(metrics.top_1_accuracy * 100).toFixed(1)}%</td><td>{(metrics.top_3_accuracy * 100).toFixed(1)}%</td><td>{metrics.evidence_coverage == null ? 'n/a' : `${(metrics.evidence_coverage * 100).toFixed(1)}%`}</td><td>{metrics.case_count}</td><td>{metrics.partial_cases}</td><td>{metrics.insufficient_evidence_cases}</td><td>{metrics.incorrect_cases}</td><td>{metrics.average_files_analyzed}</td><td>{metrics.average_functions_analyzed}</td><td>{metrics.average_graph_nodes_analyzed}</td><td>{metrics.average_analysis_time_seconds}s</td></tr>
                    ))}</tbody>
                  </table>
                </div>
              </div>
            )}
            <div className="glass-card" style={{ width: '100%' }}>
              <h3>Connected GitHub Repositories (CI/CD Enabled)</h3>
              <p className="subtitle">These repositories have GitHub Actions workflows configured.</p>
              
              {loadingRepos ? (
                <p style={{ marginTop: '20px' }}>Loading repositories...</p>
              ) : repositories.length === 0 ? (
                <p className="muted-text" style={{ marginTop: '20px' }}>No repositories with GitHub Actions found.</p>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '20px', marginTop: '20px' }}>
                  {repositories.map(repo => (
                    <div key={repo.id} className="run-item-card" style={{ padding: '20px', cursor: 'default' }}>
                      <h4 style={{ margin: '0 0 10px 0', fontSize: '1.1rem', color: '#fff' }}>{repo.name}</h4>
                      <p style={{ fontSize: '0.9rem', color: '#94a3b8', margin: '0 0 15px 0' }}>{repo.full_name}</p>
                      {repo.description && <p style={{ fontSize: '0.85rem', color: '#cbd5e1', marginBottom: '15px' }}>{repo.description}</p>}
                      
                      {repo.latest_run_id && (
                        <div style={{ marginBottom: '15px', fontSize: '0.85rem' }}>
                          <span className="label" style={{ color: '#818cf8', display: 'block', marginBottom: '5px' }}>Latest Workflow Run:</span>
                          <span>#{repo.latest_run_id} - <strong className={repo.latest_run_conclusion === 'success' ? 'text-emerald' : repo.latest_run_conclusion === 'failure' ? 'text-red' : 'text-cyan'}>{repo.latest_run_conclusion?.toUpperCase() || repo.latest_run_status?.toUpperCase() || 'UNKNOWN'}</strong></span>
                        </div>
                      )}
                      
                      <button 
                        className="btn-secondary" 
                        onClick={() => {
                          setGhRepo(repo.full_name);
                          if (repo.latest_run_id) {
                            setGhRunId(repo.latest_run_id.toString());
                          }
                          setActiveTab('github_analysis');
                        }}
                        style={{ width: '100%', display: 'flex', justifyContent: 'center', opacity: repo.latest_run_id ? 1 : 0.5 }}
                        disabled={!repo.latest_run_id}
                      >
                        {repo.latest_run_id ? 'Analyze Latest Pipeline' : 'No Runs Available'}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'runs' && (
          <div className="dashboard-grid">
            <div className="page-header" style={{ gridColumn: '1 / -1', padding: '0 20px' }}>
              <h2><History size={28} style={{ color: 'var(--accent-indigo)' }}/> Ingestion History</h2>
              <p>Real-time stream of pipeline failures analyzed by the Root Cause CI engine.</p>
            </div>
            <div className="runs-list-panel glass-card">
              <h3>Backend Ingestion Stream</h3>
              <p className="subtitle">Real responses returned from FastAPI services</p>

              {ingestedRuns.length === 0 ? (
                <p className="muted-text" style={{ marginTop: '20px' }}>
                  No failure events ingested yet. Run a <strong>GitHub Pipeline Analysis</strong>.
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
                        {selectedRun.classification?.category === 'HEALTHY' ? 'HEALTHY (PASSED)' : selectedRun.classification?.category || 'N/A'}
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
                  <p className="muted-text">Select an analysis run to view details.</p>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'github_analysis' && (
          <div style={{ padding: '0 20px' }}>
            <div className="page-header">
              <h2><Search size={28} style={{ color: 'var(--accent-indigo)' }}/> Pipeline Analysis</h2>
              <p>Fetch pipeline logs, classify root causes, and generate automated fix pull requests.</p>
            </div>
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
                    <span className="eyebrow">Analysis result</span>
                    <h3>Job: {ghResult.job_name}</h3>
                    <p className="workflow-name">Status: {ghResult.message || 'Processed'}</p>
                  </div>

                  <div className="analysis-stage-list" aria-label="Analysis stages">
                    {getAnalysisStages(ghResult).map((stage) => (
                      <div className={`analysis-stage ${stage.status.toLowerCase()}`} key={stage.name}>
                        <span className="analysis-stage-state" aria-label={stage.status}>
                          {stage.status === 'PASSED' ? '✓' : stage.status === 'FAILED' ? '!' : '—'}
                        </span>
                        <div>
                          <strong>{stage.name}</strong>
                          <span>{stage.detail}</span>
                        </div>
                        <small>{stage.status}</small>
                      </div>
                    ))}
                  </div>

                  {ghResult.classification && (
                    <div className="detail-cards-grid">
                      <div className="mini-card">
                        <span className="label">Category</span>
                        <strong className={ghResult.classification.category === 'HEALTHY' ? 'text-emerald' : 'text-cyan'}>
                          {ghResult.classification.category === 'HEALTHY' ? 'HEALTHY (PASSED)' : ghResult.classification.category}
                        </strong>
                      </div>
                      <div className="mini-card">
                        <span className="label">Comment Posted to PR</span>
                        <strong className={ghResult.comment_posted ? 'text-emerald' : 'text-red'}>
                          {ghResult.comment_posted ? 'YES' : 'NO'}
                        </strong>
                      </div>
                      {ghResult.confidence_score !== undefined && (
                        <div className="mini-card">
                          <span className="label">Confidence Score</span>
                          <strong className="text-indigo" style={{ fontSize: '1.2rem' }}>
                            {(ghResult.confidence_score * 100).toFixed(1)}%
                          </strong>
                        </div>
                      )}
                      {ghResult.author && (
                        <div className="mini-card">
                          <span className="label">Author Attribution</span>
                          <strong className="text-cyan">@{ghResult.author}</strong>
                        </div>
                      )}
                    </div>
                  )}

                  {ghResult.localization && (
                    <div className="detail-cards-grid">
                      <div className="mini-card">
                        <span className="label">Failure localization</span>
                        <strong className="text-cyan">{ghResult.localization.status}</strong>
                        <span className="muted-text">{ghResult.localization.exception_type || 'Exception not identified'}</span>
                      </div>
                      <div className="mini-card">
                        <span className="label">Failed test</span>
                        <strong>{ghResult.localization.failed_test || 'Not identified'}</strong>
                      </div>
                      <div className="mini-card">
                        <span className="label">Stack frames</span>
                        <strong>{ghResult.localization.frames?.length || 0}</strong>
                        {ghResult.localization.frames?.slice(0, 3).map((frame: any) => (
                          <span className="muted-text" key={`${frame.file_path}:${frame.line_number}`}>
                            {frame.file_path}:{frame.line_number}{frame.function ? ` in ${frame.function}` : ''}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {(ghResult.authoritative_rca?.dependency_path?.length > 0 || ghResult.dependency_paths?.length > 0) && (
                    <div className="mini-card rca-path-card">
                      <span className="label">Resolved dependency path</span>
                      <div className="rca-path-value">
                        {(ghResult.authoritative_rca?.dependency_path || ghResult.dependency_paths[0]).map((node: string, index: number, path: string[]) => (
                          <React.Fragment key={`${node}-${index}`}>
                            <code>{node}</code>
                            {index < path.length - 1 && <span aria-hidden="true">-&gt;</span>}
                          </React.Fragment>
                        ))}
                      </div>
                    </div>
                  )}

                  {(ghResult.authoritative_rca?.candidate_commits?.length > 0 || ghResult.candidate_commits?.length > 0) && (
                    <div className="mini-card candidate-summary-card">
                      <span className="label">Top root-cause candidate</span>
                      <strong className="text-cyan">{(ghResult.authoritative_rca?.candidate_commits || ghResult.candidate_commits)[0].commit_sha}</strong>
                      <span className="muted-text">{(ghResult.authoritative_rca?.candidate_commits || ghResult.candidate_commits)[0].subject || 'Commit message unavailable'}</span>
                      <span className="muted-text">Score: {((ghResult.authoritative_rca?.confidence ?? ghResult.confidence_score ?? 0) * 100).toFixed(1)}%</span>
                    </div>
                  )}

                  {(ghResult.authoritative_rca?.evidence?.length > 0 || ghResult.evidence_chain?.length > 0) && (
                    <div className="mini-card" style={{ marginTop: '15px', background: 'rgba(16, 185, 129, 0.05)', borderColor: 'rgba(16, 185, 129, 0.2)' }}>
                      <span className="label" style={{ color: '#10b981', fontWeight: 600, fontSize: '1rem', marginBottom: '10px', display: 'block' }}><span style={{display:'flex', alignItems:'center', gap:'6px'}}><Search size={16}/> Deterministic Evidence Chain</span></span>
                      <ul style={{ listStyle: 'none', padding: 0, margin: 0, fontSize: '0.95rem' }}>
                        {(ghResult.authoritative_rca?.evidence || ghResult.evidence_chain).map((ev: any, idx: number) => (
                          <li key={idx} style={{ marginBottom: '8px', display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                            <span style={{ color: '#10b981' }}>✓</span>
                            <div>
                              <strong>{ev.signal}:</strong> <span style={{ color: '#cbd5e1' }}>{ev.explanation}</span>
                              <span style={{ display: 'block', fontSize: '0.8rem', color: '#64748b', marginTop: '2px' }}>Score Contribution: {(ev.score_contribution * 100).toFixed(1)}%</span>
                            </div>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {ghResult.llm_summary && (
                    <div className="mini-card" style={{ marginTop: '15px', background: 'rgba(99, 102, 241, 0.1)', borderColor: 'rgba(99, 102, 241, 0.3)' }}>
                      <span className="label" style={{ color: '#818cf8', fontWeight: 600 }}><span style={{display:'flex', alignItems:'center', gap:'6px'}}><Terminal size={16}/> Constrained AI Root Cause Summary</span></span>
                      <p style={{ marginTop: '8px', fontSize: '0.95rem', lineHeight: '1.5' }}>
                        {ghResult.llm_summary}
                      </p>
                    </div>
                  )}

                  {ghResult.patch_code && (
                    <div className="code-snippet-box" style={{ marginTop: '15px', borderColor: 'rgba(245, 158, 11, 0.4)' }}>
                      <div className="snippet-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(245, 158, 11, 0.15)' }}>
                        <span style={{ color: '#fcd34d', fontWeight: 'bold' }}><span style={{display:'flex', alignItems:'center', gap:'6px'}}><Wrench size={16}/> Proposed Fix (Constrained Scope)</span></span>
                      </div>
                      <pre className="error-terminal" style={{ color: '#e2e8f0' }}>
                        {ghResult.patch_code}
                      </pre>
                      
                      {!ghResult.pr_url && (
                        <div className="verification-required-note" role="status">
                          <GitPullRequest size={16} />
                          <span>PR creation is locked until this patch passes scope validation and sandbox verification.</span>
                        </div>
                      )}
                      {ghResult.pr_url && (
                        <div style={{ marginTop: '15px', padding: '10px', background: 'rgba(16, 185, 129, 0.1)', border: '1px solid #10b981', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span style={{ color: '#10b981', fontWeight: 'bold' }}><CheckCircle size={16}/> Pull Request Created!</span>
                          <a href={ghResult.pr_url} target="_blank" rel="noreferrer" style={{ color: '#60a5fa', textDecoration: 'none' }}>
                            View PR #{ghResult.pr_number} on GitHub ↗
                          </a>
                        </div>
                      )}
                    </div>
                  )}

                  {ghResult.report_preview && (
                    <details style={{ marginTop: '20px' }}>
                      <summary style={{ cursor: 'pointer', color: '#94a3b8', fontSize: '0.9rem' }}>Show Raw Markdown Report</summary>
                      <div className="code-snippet-box" style={{ marginTop: '10px' }}>
                        <div className="snippet-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span>Generated Report Preview</span>
                          <button
                            type="button"
                            className="btn-secondary"
                            style={{ padding: '4px 10px', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                            onClick={() => {
                              navigator.clipboard.writeText(ghResult.report_preview);
                              setCopied(true);
                              setTimeout(() => setCopied(false), 2000);
                            }}
                          >
                            {copied ? <><CheckCircle size={14}/> Copied!</> : <><Copy size={14}/> Copy Report</>}
                          </button>
                        </div>
                        <pre className="error-terminal">
                          {ghResult.report_preview}
                        </pre>
                      </div>
                    </details>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
};
