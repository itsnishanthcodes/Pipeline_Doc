import React, { useState } from 'react';
import { loginUser, registerUser, UserAuthData, verifyGitHubCredentials } from '../services/authApi';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (user: UserAuthData) => void;
  initialMode?: 'login' | 'register';
}

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  initialMode = 'register',
}) => {
  const [mode, setMode] = useState<'login' | 'register'>(initialMode);
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [githubUsername, setGithubUsername] = useState('');
  const [githubToken, setGithubToken] = useState('');
  const [role, setRole] = useState('DevOps Engineer');

  // GitHub Connection State
  const [verifyingGh, setVerifyingGh] = useState(false);
  const [ghVerified, setGhVerified] = useState<boolean | null>(null);
  const [ghMessage, setGhMessage] = useState<string | null>(null);
  const [ghAvatar, setGhAvatar] = useState<string | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleVerifyGitHub = async () => {
    if (!githubUsername && !githubToken) {
      setGhVerified(false);
      setGhMessage('Please enter a GitHub Username or Personal Access Token to connect.');
      return;
    }

    setVerifyingGh(true);
    setGhVerified(null);
    setGhMessage(null);

    try {
      const res = await verifyGitHubCredentials(githubUsername, githubToken);
      setGhVerified(res.valid);
      setGhMessage(res.message);
      setGhAvatar(res.avatar_url || null);
    } catch (err: any) {
      setGhVerified(false);
      setGhMessage(err.message || 'Failed to connect to GitHub');
    } finally {
      setVerifyingGh(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (mode === 'register') {
        // If GitHub info was entered, verify before registering
        if (githubUsername || githubToken) {
          const check = await verifyGitHubCredentials(githubUsername, githubToken);
          if (!check.valid) {
            setError(check.message);
            setLoading(false);
            return;
          }
        }

        const response = await registerUser({
          full_name: fullName,
          email,
          password,
          github_username: githubUsername || undefined,
          github_token: githubToken || undefined,
          role,
        });
        localStorage.setItem('access_token', response.access_token);
        onSuccess(response.user);
      } else {
        const response = await loginUser({ email, password });
        localStorage.setItem('access_token', response.access_token);
        onSuccess(response.user);
      }
      onClose();
    } catch (err: any) {
      setError(err.message || 'Authentication error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content glass-panel glow-border" onClick={(e) => e.stopPropagation()}>
        <button className="close-btn" onClick={onClose}>
          &times;
        </button>

        <div className="auth-header">
          <div className="badge-chip">Root Cause CI Platform</div>
          <h2>{mode === 'register' ? 'Create Account' : 'Welcome Back'}</h2>
          <p className="auth-subtitle">
            {mode === 'register'
              ? 'Connect your GitHub repository and CI/CD pipelines'
              : 'Sign in to access live pipeline RCA & failure dashboards'}
          </p>
        </div>

        <div className="auth-tabs">
          <button
            className={`tab-btn ${mode === 'login' ? 'active' : ''}`}
            onClick={() => {
              setMode('login');
              setError(null);
            }}
          >
            Sign In
          </button>
          <button
            className={`tab-btn ${mode === 'register' ? 'active' : ''}`}
            onClick={() => {
              setMode('register');
              setError(null);
            }}
          >
            Register
          </button>
        </div>

        {error && <div className="error-alert">{error}</div>}

        <form onSubmit={handleSubmit} className="auth-form">
          {mode === 'register' && (
            <div className="form-group">
              <label>Full Name *</label>
              <input
                type="text"
                placeholder="e.g. Pranesh J S"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
              />
            </div>
          )}

          <div className="form-group">
            <label>Email Address *</label>
            <input
              type="email"
              placeholder="name@organization.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label>Password *</label>
            <input
              type="password"
              placeholder="••••••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {mode === 'register' && (
            <>
              <div className="form-row">
                <div className="form-group">
                  <label>GitHub Username *</label>
                  <input
                    type="text"
                    placeholder="e.g. Pranesh-1905"
                    value={githubUsername}
                    onChange={(e) => {
                      setGithubUsername(e.target.value);
                      setGhVerified(null);
                    }}
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Role</label>
                  <select value={role} onChange={(e) => setRole(e.target.value)}>
                    <option value="DevOps Engineer">DevOps Engineer</option>
                    <option value="SRE / Platform Engineer">SRE / Platform Engineer</option>
                    <option value="AI / ML Engineer">AI / ML Engineer</option>
                    <option value="Software Developer">Software Developer</option>
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label>GitHub Personal Access Token *</label>
                <input
                  type="password"
                  placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                  value={githubToken}
                  onChange={(e) => {
                    setGithubToken(e.target.value);
                    setGhVerified(null);
                  }}
                  required
                />
                <span className="field-hint">
                  Requires a Classic PAT with <code>repo</code> and <code>workflow</code> scopes.
                </span>
              </div>

              <div style={{ margin: '0.5rem 0 1rem 0' }}>
                <button
                  type="button"
                  onClick={handleVerifyGitHub}
                  disabled={verifyingGh}
                  className="btn-secondary"
                  style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', padding: '0.6rem' }}
                >
                  {verifyingGh ? '🔌 Verifying GitHub Account...' : '🔌 Connect & Verify GitHub Account'}
                </button>

                {ghVerified === true && (
                  <div style={{ marginTop: '0.5rem', padding: '0.5rem 0.75rem', background: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.4)', borderRadius: '6px', color: '#34d399', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    {ghAvatar && <img src={ghAvatar} alt="GitHub Avatar" style={{ width: '24px', height: '24px', borderRadius: '50%' }} />}
                    <span>✅ {ghMessage}</span>
                  </div>
                )}

                {ghVerified === false && (
                  <div style={{ marginTop: '0.5rem', padding: '0.5rem 0.75rem', background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.4)', borderRadius: '6px', color: '#f87171', fontSize: '0.85rem' }}>
                    ❌ {ghMessage}
                  </div>
                )}
              </div>
            </>
          )}

          <button type="submit" className="submit-btn primary-glow" disabled={loading}>
            {loading
              ? 'Processing...'
              : mode === 'register'
              ? 'Complete Registration'
              : 'Sign In to Dashboard'}
          </button>
        </form>
      </div>
    </div>
  );
};
