import { CircleAlert, CircleCheck, Eye, EyeOff, LoaderCircle } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { api } from '../../lib/api';
import { useAuth } from '../../lib/auth';
import { ThemeToggle } from '../../lib/theme';
import { Logo } from '../Logo';

export const ROLES = ['DevOps Engineer', 'SRE / Platform Engineer', 'Software Developer', 'AI / ML Engineer', 'Student'];

function PasswordInput({ id, value, onChange, autoComplete }: {
  id: string; value: string; onChange: (v: string) => void; autoComplete: string;
}) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="input-with-action">
      <input id={id} className="input" type={visible ? 'text' : 'password'} value={value} required minLength={8}
             autoComplete={autoComplete} onChange={(e) => onChange(e.target.value)} />
      <button type="button" className="icon-btn" onClick={() => setVisible((v) => !v)}
              aria-label={visible ? 'Hide password' : 'Show password'}>
        {visible ? <EyeOff size={16} /> : <Eye size={16} />}
      </button>
    </div>
  );
}

export function AuthPage({ mode }: { mode: 'signin' | 'signup' }) {
  const { status, signIn, register, expired } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? '/app';

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState(ROLES[0]);
  const [ghUser, setGhUser] = useState('');
  const [ghToken, setGhToken] = useState('');
  const [ghCheck, setGhCheck] = useState<{ ok: boolean; message: string } | null>(null);
  const [checking, setChecking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (status === 'signed-in') return <Navigate to={from} replace />;

  const checkGitHub = async () => {
    setChecking(true);
    setGhCheck(null);
    try {
      const res = await api.verifyGitHub(ghUser || undefined, ghToken || undefined);
      setGhCheck({ ok: res.valid, message: res.message });
    } catch (e) {
      setGhCheck({ ok: false, message: e instanceof Error ? e.message : 'GitHub could not be checked.' });
    } finally {
      setChecking(false);
    }
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === 'signin') {
        await signIn(email, password);
      } else {
        await register({
          full_name: fullName, email, password, role,
          github_username: ghUser || undefined, github_token: ghToken || undefined,
        });
      }
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.');
    } finally {
      setBusy(false);
    }
  };

  const isSignup = mode === 'signup';

  return (
    <div className="auth-page">
      <header className="auth-top">
        <Logo />
        <ThemeToggle />
      </header>
      <main className="auth-main">
        <form className="auth-card glass" onSubmit={submit} noValidate={false}>
          <h1>{isSignup ? 'Create your account' : 'Sign in'}</h1>
          <p className="muted">
            {isSignup
              ? 'Connect GitHub now or later in Settings. Your token is encrypted and never shown again.'
              : 'Pick up where you left off with your repositories and past diagnoses.'}
          </p>

          {expired && !isSignup && (
            <div className="notice"><CircleAlert size={16} /><span>Your session expired. Sign in again to continue.</span></div>
          )}
          {error && <div className="notice notice-error" role="alert"><CircleAlert size={16} /><span>{error}</span></div>}

          {isSignup && (
            <div className="field">
              <label htmlFor="name">Full name</label>
              <input id="name" className="input" value={fullName} onChange={(e) => setFullName(e.target.value)}
                     required autoComplete="name" />
            </div>
          )}
          <div className="field">
            <label htmlFor="email">Email</label>
            <input id="email" className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                   required autoComplete="email" />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <PasswordInput id="password" value={password} onChange={setPassword}
                           autoComplete={isSignup ? 'new-password' : 'current-password'} />
            {isSignup && <span className="hint">At least 8 characters.</span>}
          </div>

          {isSignup && (
            <>
              <div className="field">
                <label htmlFor="role">Role</label>
                <select id="role" className="select" value={role} onChange={(e) => setRole(e.target.value)}>
                  {ROLES.map((r) => <option key={r}>{r}</option>)}
                </select>
              </div>
              <fieldset className="auth-github">
                <legend>GitHub connection <span className="faint">(optional)</span></legend>
                <div className="field">
                  <label htmlFor="gh-user">GitHub username</label>
                  <input id="gh-user" className="input" value={ghUser} onChange={(e) => { setGhUser(e.target.value); setGhCheck(null); }}
                         autoComplete="username" spellCheck={false} />
                </div>
                <div className="field">
                  <label htmlFor="gh-token">Personal access token</label>
                  <input id="gh-token" className="input" type="password" value={ghToken}
                         onChange={(e) => { setGhToken(e.target.value); setGhCheck(null); }} autoComplete="off" spellCheck={false} />
                  <span className="hint">Needs read access to Actions and contents, and write access to open fix pull requests.</span>
                </div>
                <div className="auth-github-check">
                  <button type="button" className="btn btn-sm" onClick={checkGitHub} disabled={checking || (!ghUser && !ghToken)}>
                    {checking && <LoaderCircle size={14} className="spin" />} Check connection
                  </button>
                  {ghCheck && (
                    <span className={`small ${ghCheck.ok ? 'text-pass' : 'text-fail'}`}>
                      {ghCheck.ok ? <CircleCheck size={14} /> : <CircleAlert size={14} />} {ghCheck.message}
                    </span>
                  )}
                </div>
              </fieldset>
            </>
          )}

          <button type="submit" className="btn btn-primary btn-lg auth-submit" disabled={busy}>
            {busy && <LoaderCircle size={17} className="spin" />}
            {isSignup ? 'Create account' : 'Sign in'}
          </button>
          <p className="auth-switch muted small">
            {isSignup ? 'Already have an account? ' : 'New to Root Cause CI? '}
            <Link to={isSignup ? '/signin' : '/signup'} state={location.state}>
              {isSignup ? 'Sign in' : 'Create an account'}
            </Link>
          </p>
        </form>
      </main>
    </div>
  );
}
