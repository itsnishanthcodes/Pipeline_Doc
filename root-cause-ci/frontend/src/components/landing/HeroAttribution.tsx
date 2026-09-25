/**
 * The landing page's one orchestrated moment: a failed run on the latest commit, the evidence
 * from its log, and the lines that trace that evidence back to the commit that actually caused it.
 * Plays once on load; with reduced motion the final state is shown immediately.
 */
const COMMITS = [
  { x: 60, sha: '9e1c0d4', msg: 'Tidy imports' },
  { x: 175, sha: 'b82f310', msg: 'Update docs' },
  { x: 290, sha: 'a41f9c2', msg: 'Round totals' },
  { x: 405, sha: '4d7e21a', msg: 'Coupon field' },
  { x: 520, sha: 'f03b9e6', msg: 'Bump pytest' },
];

const LOG = [
  { text: 'FAILED tests/test_cart.py::test_total', tone: 'fail' },
  { text: 'E    assert 10.0 == 9.99', tone: 'plain' },
  { text: 'src/cart.py:41: in total', tone: 'plain' },
];

const EVIDENCE = [
  'Changed line 41 of src/cart.py',
  'Changed total(), named in the error',
  'test_cart.py imports src/cart.py',
];

export function HeroAttribution() {
  return (
    <figure className="hero-demo glass">
      <div className="hero-demo-scroll">
        <svg viewBox="0 0 600 380" role="img" aria-labelledby="hero-demo-title hero-demo-desc" className="attribution">
          <title id="hero-demo-title">How Root Cause CI traces a failed build to its cause</title>
          <desc id="hero-demo-desc">
            Five commits since the last passing run. The run on the newest commit failed. Three pieces of
            evidence from the failing test point to commit a41f9c2, not the newest commit.
          </desc>

          <text x="24" y="34" className="a-repo">acme/checkout</text>
          <rect x="146" y="19" width="50" height="22" rx="11" className="a-chip" />
          <text x="171" y="34" className="a-chip-text" textAnchor="middle">main</text>

          <line x1="36" y1="150" x2="564" y2="150" className="a-track" />

          {/* runs */}
          <g className="a-run a-run-pass">
            <rect x="14" y="94" width="94" height="26" rx="13" />
            <text x="61" y="111" textAnchor="middle">CI #41 passed</text>
          </g>
          <g className="a-run a-run-fail">
            <rect x="470" y="94" width="100" height="26" rx="13" />
            <text x="520" y="111" textAnchor="middle">CI #42 failed</text>
            <line x1="520" y1="120" x2="520" y2="138" />
          </g>

          {/* commits */}
          {COMMITS.map((c, i) => (
            <g key={c.sha} className={`a-commit ${i === 2 ? 'a-culprit' : ''} ${i === 4 ? 'a-head' : ''}`}
               style={{ animationDelay: `${120 + i * 110}ms` }}>
              <circle cx={c.x} cy="150" r="8" />
              <text x={c.x} y="180" textAnchor="middle" className="a-sha">{c.sha}</text>
              <text x={c.x} y="198" textAnchor="middle" className="a-msg">{c.msg}</text>
            </g>
          ))}

          {/* failing log */}
          <g className="a-log">
            <rect x="20" y="232" width="312" height="120" rx="14" />
            {LOG.map((l, i) => (
              <text key={l.text} x="38" y={266 + i * 28} className={`a-log-line a-log-${l.tone}`}
                    style={{ animationDelay: `${1350 + i * 140}ms` }}>
                {l.text}
              </text>
            ))}
          </g>

          {/* evidence traced back to the culprit */}
          {EVIDENCE.map((e, i) => {
            const y = 266 + i * 28;
            return (
              <g key={e} className="a-evidence" style={{ animationDelay: `${2000 + i * 180}ms` }}>
                {/* threads rise between the commit labels and meet the culprit from the lower right */}
                <path d={`M352 ${y - 4} C 362 ${y - 70}, 338 186, 301 158`} className="a-thread"
                      style={{ animationDelay: `${2000 + i * 180}ms` }} />
                <circle cx="356" cy={y - 4} r="3.5" className="a-dot" />
                <text x="366" y={y} className="a-evidence-text">{e}</text>
              </g>
            );
          })}

          {/* verdict */}
          <g className="a-verdict">
            <circle cx="290" cy="150" r="17" className="a-ring" />
            <line x1="290" y1="118" x2="290" y2="133" className="a-connector" />
            <rect x="200" y="46" width="180" height="72" rx="14" className="a-callout" />
            <text x="216" y="70" className="a-callout-label">Most likely cause</text>
            <text x="216" y="92" className="a-callout-title"><tspan className="a-sha-strong">a41f9c2</tspan> Round totals</text>
            <text x="216" y="110" className="a-callout-meta">90% confidence</text>
          </g>
        </svg>
      </div>
      <figcaption>
        An example diagnosis. The newest commit gets blamed by default, but the evidence points two commits back.
      </figcaption>
    </figure>
  );
}
