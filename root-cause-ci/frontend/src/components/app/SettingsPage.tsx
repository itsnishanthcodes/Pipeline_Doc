import { CircleCheck, KeyRound, LoaderCircle } from 'lucide-react';
import { useState, type FormEvent, type ReactNode } from 'react';
import { api } from '../../lib/api';
import { useAuth } from '../../lib/auth';
import { useToast } from '../../lib/toast';
import { ROLES } from '../auth/AuthPage';
import { PageHeader } from './AppShell';

function SettingsSection({ title, description, children }: { title: string; description: string; children: ReactNode }) {
  return (
    <section className="settings-section">
      <div className="settings-intro">
        <h2 className="panel-title">{title}</h2>
        <p className="muted small">{description}</p>
      </div>
      <div className="settings-body glass">{children}</div>
    </section>
  );
}

export function SettingsPage() {
  const { user, setUser } = useAuth();
  const notify = useToast();

  const [fullName, setFullName] = useState(user?.full_name ?? '');
  const [role, setRole] = useState(user?.role ?? ROLES[0]);
  const [savingProfile, setSavingProfile] = useState(false);

  const [ghUser, setGhUser] = useState(user?.github_username ?? '');
  const [ghToken, setGhToken] = useState('');
  const [savingGh, setSavingGh] = useState(false);
  const [ghError, setGhError] = useState<string | null>(null);

  const [currentPw, setCurrentPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [savingPw, setSavingPw] = useState(false);
  const [pwError, setPwError] = useState<string | null>(null);

  if (!user) return null;

  const saveProfile = async (e: FormEvent) => {
    e.preventDefault();
    setSavingProfile(true);
    try {
      setUser(await api.updateProfile({ full_name: fullName, role }));
      notify('Profile saved.');
    } catch (err) {
      notify(err instanceof Error ? err.message : 'The profile could not be saved.', 'error');
    } finally {
      setSavingProfile(false);
    }
  };

  const saveGitHub = async (e: FormEvent) => {
    e.preventDefault();
    setSavingGh(true);
    setGhError(null);
    try {
      const body: Record<string, unknown> = { github_username: ghUser.trim() };
      if (ghToken.trim()) body.github_token = ghToken.trim();
      setUser(await api.updateProfile(body));
      setGhToken('');
      notify('GitHub connection saved.');
    } catch (err) {
      setGhError(err instanceof Error ? err.message : 'The GitHub connection could not be saved.');
    } finally {
      setSavingGh(false);
    }
  };

  const disconnect = async () => {
    setSavingGh(true);
    try {
      setUser(await api.updateProfile({ remove_github_token: true }));
      notify('GitHub token removed.');
    } catch (err) {
      notify(err instanceof Error ? err.message : 'The token could not be removed.', 'error');
    } finally {
      setSavingGh(false);
    }
  };

  const savePassword = async (e: FormEvent) => {
    e.preventDefault();
    setSavingPw(true);
    setPwError(null);
    try {
      await api.updateProfile({ current_password: currentPw, new_password: newPw });
      setCurrentPw('');
      setNewPw('');
      notify('Password changed.');
    } catch (err) {
      setPwError(err instanceof Error ? err.message : 'The password could not be changed.');
    } finally {
      setSavingPw(false);
    }
  };

  return (
    <div className="page">
      <PageHeader title="Settings" description={`Signed in as ${user.email}.`} />

      <SettingsSection title="Profile" description="Your name appears on analyses and fix pull requests you open.">
        <form className="stack" onSubmit={saveProfile}>
          <div className="field">
            <label htmlFor="s-name">Full name</label>
            <input id="s-name" className="input" value={fullName} onChange={(e) => setFullName(e.target.value)} required />
          </div>
          <div className="field">
            <label htmlFor="s-role">Role</label>
            <select id="s-role" className="select" value={role} onChange={(e) => setRole(e.target.value)}>
              {!ROLES.includes(role) && <option>{role}</option>}
              {ROLES.map((r) => <option key={r}>{r}</option>)}
            </select>
          </div>
          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={savingProfile}>
              {savingProfile && <LoaderCircle size={15} className="spin" />} Save profile
            </button>
          </div>
        </form>
      </SettingsSection>

      <SettingsSection
        title="GitHub connection"
        description="Used to read workflow runs, logs and commits, and to open fix pull requests. The token is encrypted and never shown again."
      >
        <div className="token-state">
          <KeyRound size={18} />
          {user.has_github_token ? (
            <span><CircleCheck size={14} className="text-pass" /> A token ending in <code>{user.github_token_hint ?? '••••'}</code> is connected.</span>
          ) : <span className="muted">No token connected yet.</span>}
        </div>
        <form className="stack" onSubmit={saveGitHub}>
          <div className="field">
            <label htmlFor="s-gh-user">GitHub username</label>
            <input id="s-gh-user" className="input" value={ghUser} onChange={(e) => setGhUser(e.target.value)} spellCheck={false} />
          </div>
          <div className="field">
            <label htmlFor="s-gh-token">{user.has_github_token ? 'Replace token' : 'Personal access token'}</label>
            <input id="s-gh-token" className="input" type="password" value={ghToken} autoComplete="off"
                   onChange={(e) => setGhToken(e.target.value)} spellCheck={false}
                   placeholder={user.has_github_token ? 'Leave empty to keep the current token' : ''} />
            <span className="hint">Fine-grained tokens need Actions and Contents read access, plus Contents and Pull requests write access for fixes.</span>
          </div>
          {ghError && <p className="text-fail small" role="alert">{ghError}</p>}
          <div className="form-actions">
            {user.has_github_token && (
              <button type="button" className="btn btn-quiet btn-danger" onClick={disconnect} disabled={savingGh}>Remove token</button>
            )}
            <button type="submit" className="btn btn-primary" disabled={savingGh}>
              {savingGh && <LoaderCircle size={15} className="spin" />} Check and save
            </button>
          </div>
        </form>
      </SettingsSection>

      <SettingsSection title="Password" description="Use at least 8 characters.">
        <form className="stack" onSubmit={savePassword}>
          <div className="field">
            <label htmlFor="s-pw-current">Current password</label>
            <input id="s-pw-current" className="input" type="password" autoComplete="current-password" value={currentPw}
                   onChange={(e) => setCurrentPw(e.target.value)} required />
          </div>
          <div className="field">
            <label htmlFor="s-pw-new">New password</label>
            <input id="s-pw-new" className="input" type="password" autoComplete="new-password" minLength={8} value={newPw}
                   onChange={(e) => setNewPw(e.target.value)} required />
          </div>
          {pwError && <p className="text-fail small" role="alert">{pwError}</p>}
          <div className="form-actions">
            <button type="submit" className="btn" disabled={savingPw}>
              {savingPw && <LoaderCircle size={15} className="spin" />} Change password
            </button>
          </div>
        </form>
      </SettingsSection>
    </div>
  );
}
