import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../../lib/api';
import { useAuth } from '../../lib/auth';
import { ThemeToggle } from '../../lib/theme';
import type { EvaluationSummary } from '../../types/api';
import { Logo } from '../Logo';
import { HeroAttribution } from './HeroAttribution';

function SiteNav() {
  const { status } = useAuth();
  return (
    <header className="site-nav">
      <div className="site-nav-inner">
        <Logo />
        <nav className="site-links" aria-label="Page sections">
          <a href="#how-it-works">How it works</a>
          <a href="#results">Results</a>
          <a href="#team">Team</a>
        </nav>
        <div className="site-actions">
          <ThemeToggle />
          {status === 'signed-in' ? (
            <Link to="/app" className="btn btn-primary">Open dashboard</Link>
          ) : (
            <>
              <Link to="/signin" className="btn btn-quiet">Sign in</Link>
              <Link to="/signup" className="btn btn-primary">Get started</Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}

function Hero() {
  return (
    <section className="hero">
      <div className="hero-copy">
        <h1>Find the commit that broke your build.</h1>
        <p className="lede">
          Root Cause CI reads a failed GitHub Actions run, ranks every commit since the last passing build,
          shows the evidence behind the ranking and proposes a fix that has to pass your CI before you merge it.
        </p>
        <div className="hero-actions">
          <Link to="/signup" className="btn btn-primary btn-lg">Connect a repository</Link>
          <a href="#how-it-works" className="btn btn-lg">See how it works</a>
        </div>
        <p className="hero-footnote faint small">Works with public and private repositories through a GitHub token you control.</p>
      </div>
      <HeroAttribution />
    </section>
  );
}

const LOG_LINES: { text: string; key?: boolean }[] = [
  { text: 'Run actions/setup-python@v5' },
  { text: 'Successfully set up CPython (3.12.6)' },
  { text: 'Run pip install -r requirements.txt' },
  { text: 'Collecting fastapi==0.115.2' },
  { text: 'Successfully installed anyio-4.6.0 fastapi-0.115.2 pydantic-2.9.2 ...' },
  { text: 'Run pytest -q' },
  { text: '........................F.......                                [100%]' },
  { text: '=================================== FAILURES ===================================' },
  { text: '_________________________________ test_total __________________________________' },
  { text: '    def test_total():' },
  { text: '>       assert total([4.995, 4.995]) == 9.99' },
  { text: 'E       assert 10.0 == 9.99', key: true },
  { text: 'src/cart.py:41: in total', key: true },
  { text: 'FAILED tests/test_cart.py::test_total - assert 10.0 == 9.99', key: true },
  { text: '1 failed, 31 passed in 2.41s' },
  { text: 'Error: Process completed with exit code 1.' },
];

function NoiseToSignal() {
  const [focused, setFocused] = useState(false);
  return (
    <section className="section noise" aria-labelledby="noise-title">
      <div className="noise-copy">
        <h2 id="noise-title">A failed job leaves hundreds of log lines. A few of them matter.</h2>
        <p className="muted">
          The dashboard tells you a step failed. Finding out why means scrolling through setup output,
          dependency installs and passing tests to reach the handful of lines that explain the failure.
        </p>
        <p className="muted">
          Root Cause CI strips the timestamps and colour codes, keeps the error, the failing test and the
          file and line it points to, and removes secrets before anything is stored.
        </p>
        <button type="button" className="btn" aria-pressed={focused} onClick={() => setFocused((v) => !v)}>
          {focused ? 'Show the full log' : 'Show only the lines that matter'}
        </button>
      </div>
      <div className={`log-window glass ${focused ? 'is-focused' : ''}`}>
        <div className="log-window-bar">
          <span className="status status-fail">test</span>
          <span className="faint small">Run pytest -q</span>
        </div>
        <ol className="log-lines">
          {LOG_LINES.map((line, i) => (
            <li key={i} className={line.key ? 'log-key' : 'log-noise'}>
              <span className="log-no" aria-hidden="true">{i + 1}</span>
              <code>{line.text}</code>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

const STAGES = [
  { title: 'Read every failed job', text: 'Pull the logs, find the failing tests, the error and the file and line they point to.' },
  { title: 'Check the history', text: 'Look at earlier runs of the same job. A test that fails and passes on the same commit is flaky.' },
  { title: 'Rank the commits', text: 'Take every commit since the last passing run and score each one against the failure.' },
  { title: 'Show the evidence', text: 'Changed lines in the stack trace, changed functions in the error, imports and git blame.' },
  { title: 'Propose a fix', text: 'Give the model the real file and the culprit diff, then reject any answer that edits another file.' },
  { title: 'Verify in CI', text: 'Open a pull request and mark the fix verified only when your own CI passes on it.' },
];

function PipelineTrack() {
  return (
    <section className="section" id="how-it-works" aria-labelledby="how-title">
      <div className="section-head">
        <h2 id="how-title">How a diagnosis is built</h2>
        <p className="muted">
          Six stages run in order. The first four are deterministic, so the same failure always gets the same
          answer. The language model is only asked for a fix once that evidence exists.
        </p>
      </div>
      <ol className="track glass">
        {STAGES.map((s, i) => (
          <li key={s.title} className={`track-step ${i >= 4 ? 'is-ai' : ''}`}>
            <span className="track-node" aria-hidden="true">{i + 1}</span>
            <h3>{s.title}</h3>
            <p className="muted small">{s.text}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}

function Results() {
  const [data, setData] = useState<EvaluationSummary | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    api.evaluation().then(setData).catch(() => setFailed(true));
  }, []);

  const s = data?.summary;
  const bar = ([n, d]: [number, number]) => (d ? `${(n / d) * 100}%` : '0%');

  return (
    <section className="section results" id="results" aria-labelledby="results-title">
      <div className="section-head">
        <h2 id="results-title">Checked against the obvious guess</h2>
        <p className="muted">
          When a build breaks, the usual first move is to blame the newest commit. We measured how often that
          is right, and how often the evidence-based ranking is.
        </p>
      </div>
      {failed && <p className="muted">The evaluation results are not available right now.</p>}
      {!s && !failed && <div className="results-body glass"><div className="skeleton" style={{ height: 180 }} /></div>}
      {s && (
        <div className="results-body glass">
          <div className="compare">
            <div className="compare-row">
              <div className="compare-label">
                <strong>Blame the newest commit</strong>
                <span className="muted small">right in {s.baseline_latest_commit_top1[0]} of {s.baseline_latest_commit_top1[1]} cases</span>
              </div>
              <div className="compare-bar"><span className="is-baseline" style={{ width: bar(s.baseline_latest_commit_top1) }} /></div>
            </div>
            <div className="compare-row">
              <div className="compare-label">
                <strong>Root Cause CI ranking</strong>
                <span className="muted small">right in {s.attribution_top1[0]} of {s.attribution_top1[1]} cases</span>
              </div>
              <div className="compare-bar"><span style={{ width: bar(s.attribution_top1) }} /></div>
            </div>
          </div>
          <dl className="result-facts">
            <div>
              <dt>Failure type identified</dt>
              <dd>{s.classification_accuracy[0]} of {s.classification_accuracy[1]}</dd>
            </div>
            <div>
              <dt>Flaky failures caught</dt>
              <dd>{s.flaky_detected[0]} of {s.flaky_detected[1]}</dd>
            </div>
            <div>
              <dt>False flaky alarms</dt>
              <dd>{s.flaky_false_positives[0]} in {s.flaky_false_positives[1]}</dd>
            </div>
            <div>
              <dt>Fix aimed at the right file</dt>
              <dd>{s.target_file_accuracy[0]} of {s.target_file_accuracy[1]}</dd>
            </div>
          </dl>
          <p className="faint small results-note">
            Measured on {s.scenarios} controlled failure scenarios in the project's evaluation suite, covering
            configuration, dependency, infrastructure, regression and flaky failures. These are test fixtures,
            not a measure of accuracy on real repositories, and the language model is not involved.
          </p>
        </div>
      )}
    </section>
  );
}

const TEAM = ['Nishanth A', 'Pranesh J S', 'Rakesh A', 'Sabarish S'];

function SiteFooter() {
  return (
    <footer className="site-footer" id="team">
      <div className="footer-inner">
        <div className="footer-project">
          <Logo />
          <p className="muted">
            Root Cause Driven CI/CD Pipeline Automation, a final-year project in Artificial Intelligence and
            Data Science at Sri Krishna College of Engineering and Technology, Coimbatore.
          </p>
        </div>
        <div>
          <h3 className="footer-heading">Built by</h3>
          <ul className="footer-list">{TEAM.map((n) => <li key={n}>{n}</li>)}</ul>
        </div>
        <div>
          <h3 className="footer-heading">Guided by</h3>
          <ul className="footer-list"><li>Ms. Stenni Martin</li><li className="faint">Assistant Professor</li></ul>
        </div>
      </div>
    </footer>
  );
}

export function LandingPage() {
  return (
    <div className="site">
      <SiteNav />
      <main className="site-main">
        <Hero />
        <NoiseToSignal />
        <PipelineTrack />
        <Results />
      </main>
      <SiteFooter />
    </div>
  );
}
