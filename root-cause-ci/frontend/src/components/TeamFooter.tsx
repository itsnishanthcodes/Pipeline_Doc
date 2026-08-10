import React from 'react';

export const TeamFooter: React.FC = () => {
  return (
    <footer className="footer-container" id="team">
      <div className="footer-content">
        <div className="footer-col">
          <div className="footer-brand">Root Cause CI</div>
          <p className="footer-desc">
            Evidence-first CI/CD failure diagnosis and verified remediation platform.
          </p>
        </div>

        <div className="footer-col">
          <h4>Platform Capabilities</h4>
          <ul className="footer-nav">
            <li>Log Normalization & Triage</li>
            <li>Graph-Aware Fault Localization</li>
            <li>Sandbox Rerun Verification</li>
            <li>Automated Fix PR Generation</li>
          </ul>
        </div>

        <div className="footer-col">
          <h4>Integration & Standards</h4>
          <p className="dept-info">GitHub Actions & Webhook Infrastructure</p>
          <p className="phase-info">RESTful API & Microservice Compatibility</p>
        </div>
      </div>

      <div className="footer-bottom">
        <p>© 2026 Root Cause CI Pipeline Automation • All Rights Reserved</p>
      </div>
    </footer>
  );
};
