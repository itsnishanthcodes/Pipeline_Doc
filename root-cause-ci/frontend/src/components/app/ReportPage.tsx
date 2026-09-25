import { ArrowLeft, CircleAlert } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../../lib/api';
import type { AnalysisReport } from '../../types/analysis';
import { ReportView } from './ReportView';

export function ReportPage() {
  const { id } = useParams();
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setReport(null);
    setError(null);
    const reportId = Number(id);
    if (!Number.isFinite(reportId)) {
      setError('This report link is not valid.');
      return;
    }
    api.report(reportId).then(setReport).catch((e) => setError(e instanceof Error ? e.message : 'The report could not be loaded.'));
  }, [id]);

  const onChange = useCallback((r: AnalysisReport) => setReport(r), []);

  return (
    <div className="page">
      <Link to="/app/history" className="back-link"><ArrowLeft size={15} /> History</Link>
      {error && <div className="notice notice-error" role="alert"><CircleAlert size={16} /><span>{error}</span></div>}
      {!report && !error && (
        <div className="report">
          <span className="skeleton" style={{ height: 40, width: '45%' }} />
          <span className="skeleton" style={{ height: 120 }} />
          <span className="skeleton" style={{ height: 260 }} />
        </div>
      )}
      {report && <ReportView report={report} onChange={onChange} />}
    </div>
  );
}
