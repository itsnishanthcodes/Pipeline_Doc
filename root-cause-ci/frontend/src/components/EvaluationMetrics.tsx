import React from 'react';
import type { HealthResponse } from '../types/health';

interface EvaluationMetricsProps {
  health: HealthResponse | null;
  error: string | null;
}

export const EvaluationMetrics: React.FC<EvaluationMetricsProps> = ({ health, error }) => {
  return (
    <section className="section-container" id="status">
      <div className="section-header">
        <span className="section-subtitle">Connection status</span>
        <h2 className="section-title">The service behind the workspace</h2>
      </div>

      <div className="glass-card live-status-panel">
        <div className="status-panel-header">
          <div>
            <h3>Backend connection</h3>
            <p className="subtitle">The status below comes from the running FastAPI service.</p>
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
            {error || 'Checking the backend connection...'}
          </div>
        )}
      </div>
    </section>
  );
};
