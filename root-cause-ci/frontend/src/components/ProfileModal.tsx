import React, { useEffect, useState } from 'react';
import { fetchProfile, updateProfile, UserAuthData } from '../services/authApi';

interface ProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentUser: UserAuthData;
  onUpdateUser: (updatedUser: UserAuthData) => void;
}

export const ProfileModal: React.FC<ProfileModalProps> = ({
  isOpen,
  onClose,
  currentUser,
  onUpdateUser,
}) => {
  const [fullName, setFullName] = useState(currentUser.full_name || '');
  const [githubUsername, setGithubUsername] = useState(currentUser.github_username || '');
  const [githubToken, setGithubToken] = useState(currentUser.github_token || '');
  const [role, setRole] = useState(currentUser.role || 'DevOps Engineer');

  // Change password fields
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');

  const [showToken, setShowToken] = useState(false);
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      setError(null);
      setSuccessMsg(null);
      setCurrentPassword('');
      setNewPassword('');

      const token = localStorage.getItem('access_token');
      if (token) {
        setFetching(true);
        fetchProfile(token)
          .then((profile) => {
            setFullName(profile.full_name || '');
            setGithubUsername(profile.github_username || '');
            setGithubToken(profile.github_token || '');
            setRole(profile.role || 'DevOps Engineer');
          })
          .catch(() => {
            // Keep default state from currentUser prop
          })
          .finally(() => {
            setFetching(false);
          });
      }
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccessMsg(null);

    const token = localStorage.getItem('access_token');
    if (!token) {
      setError('Authentication token expired. Please log in again.');
      setLoading(false);
      return;
    }

    try {
      const updated = await updateProfile(token, {
        full_name: fullName,
        github_username: githubUsername,
        github_token: githubToken,
        role,
        current_password: currentPassword || undefined,
        new_password: newPassword || undefined,
      });

      onUpdateUser(updated);
      setSuccessMsg('Profile and credentials updated successfully! ⚡');
      setCurrentPassword('');
      setNewPassword('');
    } catch (err: any) {
      setError(err.message || 'Failed to update profile');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content glass-panel glow-border" style={{ maxWidth: '540px' }} onClick={(e) => e.stopPropagation()}>
        <button className="close-btn" onClick={onClose}>
          &times;
        </button>

        <div className="auth-header">
          <div className="badge-chip">Account & Integration Manager</div>
          <h2>Profile & Credentials</h2>
          <p className="auth-subtitle">
            Manage your GitHub ID, Personal Access Token (PAT), and account password
          </p>
        </div>

        {fetching && <div className="loading-spinner">Fetching live profile details...</div>}
        {error && <div className="error-alert">{error}</div>}
        {successMsg && <div className="success-alert" style={{ background: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.4)', color: '#34d399', padding: '0.75rem 1rem', borderRadius: '8px', marginBottom: '1rem', fontSize: '0.9rem' }}>{successMsg}</div>}

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label>Email Address</label>
            <input type="email" value={currentUser.email} disabled style={{ opacity: 0.6, cursor: 'not-allowed' }} />
            <span className="field-hint">Email cannot be changed</span>
          </div>

          <div className="form-group">
            <label>Full Name</label>
            <input
              type="text"
              placeholder="e.g. Pranesh J S"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>GitHub Username (GitHub ID) 🐙</label>
              <input
                type="text"
                placeholder="e.g. Pranesh-1905"
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
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
              <label style={{ margin: 0 }}>GitHub Personal Access Token (PAT) 🔑</label>
              <button
                type="button"
                onClick={() => setShowToken(!showToken)}
                style={{ background: 'none', border: 'none', color: 'var(--primary-glow, #3b82f6)', fontSize: '0.8rem', cursor: 'pointer', textDecoration: 'underline' }}
              >
                {showToken ? 'Hide Token' : 'Show Token'}
              </button>
            </div>
            <input
              type={showToken ? 'text' : 'password'}
              placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
              value={githubToken}
              onChange={(e) => setGithubToken(e.target.value)}
            />
            <span className="field-hint">
              Used to fetch private pipeline runs, logs, and post automated RCA report comments to PRs.
            </span>
          </div>

          <div style={{ marginTop: '1.25rem', paddingTop: '1rem', borderTop: '1px solid rgba(255, 255, 255, 0.1)' }}>
            <h4 style={{ margin: '0 0 0.75rem 0', fontSize: '0.95rem', color: 'var(--text-primary, #f3f4f6)' }}>
              🔒 Change Password (Optional)
            </h4>
            <div className="form-row">
              <div className="form-group">
                <label>Current Password</label>
                <input
                  type="password"
                  placeholder="••••••••••••"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>New Password</label>
                <input
                  type="password"
                  placeholder="••••••••••••"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                />
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem' }}>
            <button type="button" className="btn-secondary" onClick={onClose} style={{ flex: 1 }}>
              Cancel
            </button>
            <button type="submit" className="submit-btn primary-glow" disabled={loading} style={{ flex: 2, marginTop: 0 }}>
              {loading ? 'Saving Changes...' : 'Save Profile Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
