import React, { useState } from 'react';

export const MethodologyFlow: React.FC = () => {
  const [activeStep, setActiveStep] = useState(0);

  const steps = [
    {
      phase: 'Phase 1',
      title: 'Data Collection & Preprocessing',
      icon: '📡',
      detail:
        'Capture build/test logs, stack traces, exit codes, and pipeline metadata via webhooks from GitHub Actions/Jenkins. Strip noise & chunk log context.',
    },
    {
      phase: 'Phase 2',
      title: 'Failure Classification',
      icon: '⚡',
      detail:
        'Compare log/error signatures against historical run patterns to label failures as Flaky (transient) vs. Real (code fault) before running expensive RCA.',
    },
    {
      phase: 'Phase 3',
      title: 'Root Cause Analysis (RCA)',
      icon: '🧠',
      detail:
        'For real failures, the LLM reasons over structured log context, dependency graphs, and historical incident records to pinpoint faulty stages.',
    },
    {
      phase: 'Phase 4',
      title: 'Fix Generation & Sandbox Verification',
      icon: '🛡️',
      detail:
        'Generate candidate patch suggestions, apply them inside an isolated Docker execution sandbox, and rerun the failed stage to verify correctness.',
    },
    {
      phase: 'Phase 5',
      title: 'Evaluation & PR Automation',
      icon: '🚀',
      detail:
        'Benchmark against 30-50 real-world open-source pipeline failures. Propose verified fix PRs with minimal human intervention.',
    },
  ];

  return (
    <section className="section-container" id="architecture">
      <div className="section-header">
        <span className="section-subtitle">System Architecture</span>
        <h2 className="section-title">5-Phase Pipeline Methodology</h2>
        <p className="section-description">
          An automated end-to-end flow taking raw CI/CD failure logs to a verified, sandboxed fix.
        </p>
      </div>

      <div className="pipeline-steps-grid">
        {steps.map((step, idx) => (
          <div
            key={idx}
            className={`step-card glass-card ${activeStep === idx ? 'active-step' : ''}`}
            onClick={() => setActiveStep(idx)}
          >
            <div className="step-badge">{step.phase}</div>
            <div className="step-icon">{step.icon}</div>
            <h3 className="step-title">{step.title}</h3>
            <p className="step-detail">{step.detail}</p>
          </div>
        ))}
      </div>
    </section>
  );
};
