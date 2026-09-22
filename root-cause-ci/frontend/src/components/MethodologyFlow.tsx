import React, { useState } from 'react';

export const MethodologyFlow: React.FC = () => {
  const [activeStep, setActiveStep] = useState(0);

  const steps = [
    {
      phase: '01',
      title: 'Collect the run',
      icon: '01',
      detail:
        'Fetch the workflow run, failed job, log output, pull request, and changed files from GitHub Actions.',
    },
    {
      phase: '02',
      title: 'Classify the failure',
      icon: '02',
      detail:
        'Use deterministic log signals to separate configuration, infrastructure, dependency, and code failures.',
    },
    {
      phase: '03',
      title: 'Build the evidence',
      icon: '03',
      detail:
        'Compare the failure with changed files, functions, commit timing, and the available code structure.',
    },
    {
      phase: '04',
      title: 'Review a report',
      icon: '04',
      detail:
        'Read the confidence score, evidence chain, classification, and optional AI summary before taking action.',
    },
    {
      phase: '05',
      title: 'Choose the next step',
      icon: '05',
      detail:
        'Use the report as a starting point for a code review or a proposed fix. The final decision stays with the engineer.',
    },
  ];

  return (
    <section className="section-container" id="workflow">
      <div className="section-header">
        <span className="section-subtitle">How it works</span>
        <h2 className="section-title">A review path built around evidence</h2>
        <p className="section-description">
          Each step leaves room for an engineer to inspect the source of the conclusion.
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
