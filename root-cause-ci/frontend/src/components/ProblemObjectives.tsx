import React from 'react';

export const ProblemObjectives: React.FC = () => {
  return (
    <section className="section-container">
      <div className="two-col-grid">
        <div className="glass-card info-panel border-red">
          <div className="panel-badge red">Before the review</div>
          <h3>What usually gets lost in a failed run</h3>
          <ul className="custom-list">
            <li>
              <strong>Too much log output:</strong> The useful line is often buried inside a long build or test log.
            </li>
            <li>
              <strong>Context is split:</strong> The run, pull request, changed files, and commit history live in different places.
            </li>
            <li>
              <strong>Diagnosis becomes guesswork:</strong> Without a clear trail, engineers repeat the same investigation by hand.
            </li>
          </ul>
        </div>

        <div className="glass-card info-panel border-cyan">
          <div className="panel-badge cyan">What this workspace does</div>
          <h3>Bring the relevant evidence together</h3>
          <ul className="custom-list">
            <li>
              <strong>Start with rules:</strong> Deterministic classification gives the report a traceable first conclusion.
            </li>
            <li>
              <strong>Link code context:</strong> Changed files, functions, commits, and pull requests stay beside the failure.
            </li>
            <li>
              <strong>Keep a human in the loop:</strong> The report suggests where to look; it does not make a merge decision for you.
            </li>
          </ul>
        </div>
      </div>
    </section>
  );
};
