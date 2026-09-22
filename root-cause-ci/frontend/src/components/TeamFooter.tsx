import React from 'react';

export const TeamFooter: React.FC = () => {
  return (
    <footer className="footer-container" id="team">
      <div className="footer-content">
        <div className="footer-col">
          <div className="footer-brand">Root Cause CI</div>
          <p className="footer-desc">
            A small workspace for turning a failed CI run into a reviewable explanation.
          </p>
        </div>

        <div className="footer-col">
          <h4>In this build</h4>
          <ul className="footer-nav">
            <li>GitHub Actions run analysis</li>
            <li>Failure classification</li>
            <li>Commit and file evidence</li>
            <li>Analysis history</li>
          </ul>
        </div>

        <div className="footer-col">
          <h4>Connections</h4>
          <p className="dept-info">GitHub Actions and GitHub repositories</p>
          <p className="phase-info">FastAPI and PostgreSQL-backed reports</p>
        </div>
      </div>

      <div className="footer-bottom">
        <p>© {new Date().getFullYear()} Root Cause CI</p>
      </div>
    </footer>
  );
};
