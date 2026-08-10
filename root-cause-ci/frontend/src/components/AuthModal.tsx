import React, { useState } from 'react';
import { loginUser, registerUser, UserAuthData } from '../services/authApi';

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

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (mode === 'register') {
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
                  <label>GitHub Username (Optional)</label>
                  <input
                    type="text"
                    placeholder="e.g. octocat"
                    value={githubUsername}
                    onChange={(e) => setGithubUsername(e.target.value)}
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
                <label>GitHub Personal Access Token (Optional)</label>
                <input
                  type="password"
                  placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                  value={githubToken}
                  onChange={(e) => setGithubToken(e.target.value)}
                />
                <span className="field-hint">
                  Used by backend webhook ingestion & fix PR generation.
                </span>
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
