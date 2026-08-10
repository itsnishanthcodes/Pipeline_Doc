import React from 'react';

export const ProblemObjectives: React.FC = () => {
  return (
    <section className="section-container">
      <div className="two-col-grid">
        <div className="glass-card info-panel border-red">
          <div className="panel-badge red">Problem Statement</div>
          <h3>The Challenge in Modern CI/CD</h3>
          <ul className="custom-list">
            <li>
              <strong>Frequent CI Failures:</strong> Organizations suffer from flaky tests, config drift, and regressions.
            </li>
            <li>
              <strong>Log Analysis Overload:</strong> Modern microservices generate massive multi-stage build logs.
            </li>
            <li>
              <strong>High MTTR & Delayed Releases:</strong> Manual RCA by engineers is slow, costly, and distracts from feature delivery.
            </li>
          </ul>
        </div>

        <div className="glass-card info-panel border-cyan">
          <div className="panel-badge cyan">Objectives & Innovation</div>
          <h3>LLM Triage & Sandbox Solution</h3>
          <ul className="custom-list">
            <li>
              <strong>Triage-First Design:</strong> Flaky vs Real classification gates expensive LLM reasoning.
            </li>
            <li>
              <strong>Structured Context:</strong> Avoids context rot by stripping raw log noise before LLM analysis.
            </li>
            <li>
              <strong>Deterministic Sandbox Rerun:</strong> Never merges fixes based on LLM confidence alone — only after verified sandbox runs pass.
            </li>
          </ul>
        </div>
      </div>
    </section>
  );
};
