import React from 'react';

interface NavbarProps {
  onOpenAuth: (mode: 'login' | 'register') => void;
  currentUser: any;
  onLogout: () => void;
  onOpenProfile?: () => void;
  theme: 'dark' | 'light';
  onToggleTheme: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  onOpenAuth,
  currentUser,
  onLogout,
  onOpenProfile,
  theme,
  onToggleTheme,
}) => {
  return (
    <header className="navbar-header glass-nav">
      <div className="nav-container">
        <div className="brand-group">
          <div className="brand-logo">
            <span className="logo-spark">⚡</span>
          </div>
          <div>
            <div className="brand-name">Root Cause CI</div>
            <div className="brand-tagline">Automated Intelligence Platform</div>
          </div>
        </div>

        <nav className="nav-links">
          <a href="#overview">Overview</a>
          <a href="#architecture">Architecture</a>
          <a href="#innovations">Capabilities</a>
          <a href="#metrics">Metrics</a>
        </nav>

        <div className="nav-actions">
          <button className="theme-toggle-btn" onClick={onToggleTheme} title="Toggle Light / Dark Theme">
            {theme === 'dark' ? '☀️' : '🌙'}
          </button>
          
          <span className="phase-badge pulse">Production Prototype</span>

          {currentUser ? (
            <div className="user-menu" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <button 
                className="user-greeting" 
                onClick={onOpenProfile}
                title="Manage Profile & GitHub Credentials"
                style={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)', padding: '0.35rem 0.75rem', borderRadius: '20px', color: 'var(--text-primary)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.85rem' }}
              >
                <span>👋</span>
                <span>{currentUser.full_name}</span>
                <span style={{ fontSize: '0.75rem', opacity: 0.7 }}>⚙️ Profile</span>
              </button>
              <button className="btn-secondary" onClick={onLogout}>
                Logout
              </button>
            </div>
          ) : (
            <>
              <button className="btn-secondary" onClick={() => onOpenAuth('login')}>
                Sign In
              </button>
              <button className="btn-primary-small" onClick={() => onOpenAuth('register')}>
                Register
              </button>
            </>
          )}
        </div>
      </div>
    </header>
  );
};
