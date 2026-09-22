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
        <div className="hero-kicker animate-fade-down">For teams investigating failed GitHub Actions runs</div>

        <h1 className="hero-title animate-title">
          A clearer way to review a failed CI run
        </h1>

        <p className="hero-description animate-fade-up">
          Root Cause CI collects the run log, classifies the failure, and brings the relevant
          commit and pull request context into one review. Start with the evidence, then decide what to change.
        </p>

        <div className="hero-cta-group animate-fade-up-delay">
          <button className="get-started-btn pulse-glow" onClick={onGetStarted}>
            <span>Open the workspace</span>
            <span className="btn-icon">→</span>
          </button>
          
          <a href="#architecture" className="btn-outline">
            See the workflow
          </a>
        </div>

        <div className="hero-note"><span className="status-dot" /> Connect a GitHub account to inspect your own runs</div>
      </div>
    </section>
  );
};
