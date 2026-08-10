import { useEffect, useState } from 'react';
import { fetchHealth } from './services/api';
import type { HealthResponse } from './types/health';

function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : 'Failed to load health status');
      });
  }, []);

  return (
    <main className="app-shell">
      <section className="hero-card">
        <div>
          <p className="eyebrow">Phase 1</p>
          <h1>Root Cause Driven CI/CD Pipeline Automation</h1>
          <p className="lede">
            Evidence-first diagnosis scaffold with FastAPI, PostgreSQL, and a React dashboard shell.
          </p>
        </div>

        <div className="status-grid">
          <article className="status-card">
            <span className="label">Backend</span>
            <strong>FastAPI</strong>
          </article>
          <article className="status-card">
            <span className="label">Database</span>
            <strong>PostgreSQL</strong>
          </article>
          <article className="status-card">
            <span className="label">Frontend</span>
            <strong>React + TypeScript</strong>
          </article>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>System Health</h2>
          <p>Live response from the backend health endpoint.</p>
        </div>

        {health ? (
          <div className="health-grid">
            <div>
              <span className="label">Status</span>
              <strong>{health.status}</strong>
            </div>
            <div>
              <span className="label">Service</span>
              <strong>{health.service}</strong>
            </div>
            <div>
              <span className="label">Environment</span>
              <strong>{health.environment}</strong>
            </div>
            <div>
              <span className="label">Database</span>
              <strong>{health.database}</strong>
            </div>
          </div>
        ) : (
          <p className="muted">Loading health status...</p>
        )}

        {error ? <p className="error">{error}</p> : null}
      </section>
    </main>
  );
}

export default App;
