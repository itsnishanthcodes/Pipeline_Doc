import { RefreshCw, Zap } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../../lib/api';
import { categoryLabel, shortSha, timeAgo } from '../../lib/format';
import type { AnalysisReport } from '../../types/analysis';
import { PageHeader } from './AppShell';

const FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'failures', label: 'Failures' },
  { id: 'auto', label: 'From webhooks' },
  { id: 'fixes', label: 'With a fix pull request' },
] as const;

type FilterId = (typeof FILTERS)[number]['id'];

const VERIFY_LABEL: Record<string, string> = {
  pending: 'Fix waiting for CI', running: 'Fix running in CI', verified: 'Fix verified', failed: 'Fix failed CI',
};

export function HistoryPage() {
  const [reports, setReports] = useState<AnalysisReport[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterId>('all');
  const [query, setQuery] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setReports(await api.history());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'History could not be loaded.');
      setReports((r) => r ?? []);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const timer = window.setInterval(load, 30000);
    return () => window.clearInterval(timer);
  }, [load]);

  const visible = useMemo(() => (reports ?? []).filter((r) => {
    if (filter === 'failures' && r.is_healthy) return false;
    if (filter === 'auto' && r.source !== 'webhook') return false;
    if (filter === 'fixes' && !r.fix_pr_url) return false;
    return r.repository.toLowerCase().includes(query.trim().toLowerCase());
  }), [reports, filter, query]);

  return (
    <div className="page">
      <PageHeader
        title="History"
        description="Every diagnosis you ran, plus failures analysed automatically when GitHub reports them."
        actions={(
          <button type="button" className="btn" onClick={load} disabled={loading}>
            <RefreshCw size={15} className={loading ? 'spin' : ''} /> Refresh
          </button>
        )}
      />
      {error && <p className="text-fail">{error}</p>}

      <div className="list-panel glass">
        <div className="list-toolbar">
          <div className="segmented" role="tablist" aria-label="Filter history">
            {FILTERS.map((f) => (
              <button key={f.id} type="button" role="tab" aria-selected={filter === f.id}
                      className={filter === f.id ? 'is-active' : ''} onClick={() => setFilter(f.id)}>
                {f.label}
              </button>
            ))}
          </div>
          <input className="input toolbar-search" type="search" placeholder="Filter by repository" value={query}
                 onChange={(e) => setQuery(e.target.value)} aria-label="Filter by repository" />
        </div>

        {reports === null ? (
          <div className="rows">{[0, 1, 2].map((i) => <div key={i} className="row"><span className="skeleton" style={{ height: 20, width: '65%' }} /></div>)}</div>
        ) : visible.length === 0 ? (
          <div className="list-empty">
            {reports.length === 0 ? (
              <>
                <p className="muted">No diagnoses yet. Analyze a failed run to see it here.</p>
                <Link to="/app/analyze" className="btn btn-primary btn-sm">Analyze a run</Link>
              </>
            ) : <p className="muted">Nothing matches this filter.</p>}
          </div>
        ) : (
          <ul className="rows">
            {visible.map((r) => {
              const culprit = r.candidates?.[0];
              return (
                <li key={r.report_id}>
                  <Link to={`/app/reports/${r.report_id}`} className="row history-row">
                    <span className={`status status-${r.is_healthy ? 'pass' : 'fail'}`}>{r.is_healthy ? 'Passed' : 'Failed'}</span>
                    <div className="history-main">
                      <strong>{r.repository}</strong>
                      <span className="faint small run-meta">
                        <span>Run #{r.run_id}</span>
                        {r.branch && <code>{r.branch}</code>}
                        <span>{timeAgo(r.created_at)}</span>
                        {r.source === 'webhook' && <span className="tag"><Zap size={12} /> automatic</span>}
                      </span>
                    </div>
                    <div className="history-verdict">
                      <span>{categoryLabel(r.classification?.category)}</span>
                      {!r.is_healthy && culprit && (
                        <span className="faint small">Likely <span className="mono">{shortSha(culprit.commit_sha)}</span></span>
                      )}
                    </div>
                    <div className="history-fix">
                      {r.verification_status && (
                        <span className={`status status-${r.verification_status === 'verified' ? 'pass' : r.verification_status === 'failed' ? 'fail' : 'pending'}`}>
                          {VERIFY_LABEL[r.verification_status]}
                        </span>
                      )}
                    </div>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
