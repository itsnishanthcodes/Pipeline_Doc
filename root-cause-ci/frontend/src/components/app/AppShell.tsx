import { FolderGit2, History, LogOut, ScanSearch, Settings } from 'lucide-react';
import type { ReactNode } from 'react';
import { Navigate, NavLink, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../../lib/auth';
import { ThemeToggle } from '../../lib/theme';
import { Logo } from '../Logo';

export function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  const location = useLocation();
  if (status === 'loading') {
    return <div className="boot"><span className="skeleton boot-bar" /></div>;
  }
  if (status === 'signed-out') {
    return <Navigate to="/signin" replace state={{ from: location.pathname + location.search }} />;
  }
  return <>{children}</>;
}

const NAV = [
  { to: '/app/repositories', label: 'Repositories', icon: FolderGit2 },
  { to: '/app/analyze', label: 'Analyze a run', icon: ScanSearch },
  { to: '/app/history', label: 'History', icon: History },
  { to: '/app/settings', label: 'Settings', icon: Settings },
];

export function AppShell() {
  const { user, signOut } = useAuth();
  const initials = (user?.full_name ?? '?').split(/\s+/).map((p) => p[0]).slice(0, 2).join('').toUpperCase();

  return (
    <div className="app">
      <aside className="rail glass">
        <div className="rail-top">
          <Logo to="/app" />
        </div>
        <nav className="rail-nav" aria-label="Main">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} className={({ isActive }) => `rail-link ${isActive ? 'is-active' : ''}`}>
              <Icon size={18} strokeWidth={1.8} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="rail-bottom">
          <div className="rail-user">
            <span className="avatar" aria-hidden="true">{initials}</span>
            <span className="rail-user-text">
              <strong>{user?.full_name}</strong>
              <span className="faint small">{user?.github_username ? `@${user.github_username}` : user?.email}</span>
            </span>
          </div>
          <div className="rail-actions">
            <ThemeToggle />
            <button type="button" className="icon-btn" onClick={signOut} aria-label="Sign out" title="Sign out">
              <LogOut size={17} />
            </button>
          </div>
        </div>
      </aside>
      <main className="app-main" id="main">
        <Outlet />
      </main>
    </div>
  );
}

export function PageHeader({ title, description, actions }: { title: string; description?: ReactNode; actions?: ReactNode }) {
  return (
    <header className="page-header">
      <div>
        <h1>{title}</h1>
        {description && <p className="muted">{description}</p>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  );
}
