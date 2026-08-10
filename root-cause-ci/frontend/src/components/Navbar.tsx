import React from 'react';

interface NavbarProps {
  onOpenAuth: (mode: 'login' | 'register') => void;
  currentUser: any;
  onLogout: () => void;
  theme: 'dark' | 'light';
  onToggleTheme: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  onOpenAuth,
  currentUser,
  onLogout,
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
            <div className="user-menu">
              <span className="user-greeting">👋 {currentUser.full_name}</span>
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
