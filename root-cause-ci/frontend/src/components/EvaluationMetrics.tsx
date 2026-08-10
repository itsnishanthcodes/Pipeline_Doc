import React from 'react';
import type { HealthResponse } from '../types/health';

interface EvaluationMetricsProps {
  health: HealthResponse | null;
  error: string | null;
}

export const EvaluationMetrics: React.FC<EvaluationMetricsProps> = ({ health, error }) => {
  return (
    <section className="section-container" id="metrics">
      <div className="section-header">
        <span className="section-subtitle">Evaluation & Metrics</span>
        <h2 className="section-title">Measurable Outcomes & Live Status</h2>
      </div>

      <div className="metrics-grid">
        <div className="metric-box glass-card">
          <div className="metric-header">Classification Accuracy</div>
          <div className="metric-value gradient-text">&ge; 85%</div>
          <p className="metric-desc">Precision & recall separation of Flaky vs Real pipeline failures.</p>
        </div>

        <div className="metric-box glass-card">
          <div className="metric-header">Diagnostic Efficiency (MTTD)</div>
          <div className="metric-value gradient-text">&lt; 5 mins</div>
          <p className="metric-desc">90%+ reduction in Mean Time To Diagnosis per failure.</p>
        </div>

        <div className="metric-box glass-card">
          <div className="metric-header">Benchmark Coverage</div>
          <div className="metric-value gradient-text">30 - 50</div>
          <p className="metric-desc">Open-source pipeline failure evaluation cases.</p>
        </div>
      </div>

      <div className="glass-card live-status-panel">
        <div className="status-panel-header">
          <div>
            <h3>Live Backend System Connection</h3>
            <p className="subtitle">Real-time status from FastAPI backend server endpoint</p>
          </div>
          <div className={`status-indicator ${health ? 'online' : 'offline'}`}>
            <span className="dot" />
            <span>{health ? 'Backend Connected' : 'Connecting / Offline'}</span>
          </div>
        </div>

        {health ? (
          <div className="health-details-grid">
            <div className="detail-item">
              <span className="item-label">API Service</span>
              <span className="item-val">{health.service}</span>
            </div>
            <div className="detail-item">
              <span className="item-label">Environment</span>
              <span className="item-val">{health.environment}</span>
            </div>
            <div className="detail-item">
              <span className="item-label">Health Status</span>
              <span className="item-val highlight-green">{health.status}</span>
            </div>
            <div className="detail-item">
              <span className="item-label">Database Connection</span>
              <span className="item-val">{health.database}</span>
            </div>
          </div>
        ) : (
          <div className="error-box">
            {error || 'Attempting connection to FastAPI server at http://localhost:8000/health...'}
          </div>
        )}
      </div>
    </section>
  );
};
