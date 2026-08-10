import type { HealthResponse } from '../types/health';

interface HealthCardProps {
  health: HealthResponse;
}

export function HealthCard({ health }: HealthCardProps) {
  return (
    <article>
      <h3>Backend Health</h3>
      <dl>
        <div>
          <dt>Status</dt>
          <dd>{health.status}</dd>
        </div>
        <div>
          <dt>Database</dt>
          <dd>{health.database}</dd>
        </div>
      </dl>
    </article>
  );
}
