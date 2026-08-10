import React from 'react';

interface HeroSectionProps {
  onGetStarted: () => void;
  scrollY: number;
}

export const HeroSection: React.FC<HeroSectionProps> = ({ onGetStarted, scrollY }) => {
  return (
    <section className="hero-container" id="overview">
      <div
        className="parallax-bg-glow"
        style={{ transform: `translateY(${scrollY * 0.3}px)` }}
      />
      
      <div className="hero-content">
        <div className="hero-badge animate-fade-down">
          <span>Enterprise Reliability Engine</span>
          <span className="badge-dot" />
          <span>LLM-Driven Diagnostic Loop</span>
        </div>

        <h1 className="hero-title animate-title">
          Root Cause Driven <br />
          <span className="gradient-text">CI/CD Pipeline Automation</span>
        </h1>

        <p className="hero-description animate-fade-up">
          Evidence-first CI/CD failure diagnosis and verified remediation.
          Automated triage separating <strong>Flaky</strong> vs <strong>Real</strong> failures, 
          LLM root cause analysis, and sandboxed fix validation before code merge.
        </p>

        <div className="hero-cta-group animate-fade-up-delay">
          <button className="get-started-btn pulse-glow" onClick={onGetStarted}>
            <span>Get Started</span>
            <span className="btn-icon">→</span>
          </button>
          
          <a href="#architecture" className="btn-outline">
            Explore Architecture
          </a>
        </div>

        <div className="hero-stats-row">
          <div className="stat-card glass-card">
            <span className="stat-number gradient-text">&ge; 85%</span>
            <span className="stat-label">Classification Accuracy</span>
          </div>
          <div className="stat-card glass-card">
            <span className="stat-number gradient-text">&lt; 5 min</span>
            <span className="stat-label">Mean Time To Diagnosis (90%+ reduction)</span>
          </div>
          <div className="stat-card glass-card">
            <span className="stat-number gradient-text">30-50</span>
            <span className="stat-label">Benchmark Test Pipelines</span>
          </div>
        </div>
      </div>
    </section>
  );
};
