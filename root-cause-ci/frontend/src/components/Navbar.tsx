import React from 'react';
import { LogOut, Moon, Settings, Sun, UserCircle } from 'lucide-react';
import type { UserAuthData } from '../services/authApi';

interface NavbarProps {
  onOpenAuth: (mode: 'login' | 'register') => void;
  currentUser: UserAuthData | null;
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
          <div className="brand-logo" aria-hidden="true">
            <span className="logo-mark">rc</span>
          </div>
          <div>
            <div className="brand-name">Root Cause CI</div>
            <div className="brand-tagline">CI failure review</div>
          </div>
        </div>

        {!currentUser && (
          <nav className="nav-links" aria-label="Main navigation">
            <a href="#overview">Overview</a>
            <a href="#workflow">Workflow</a>
            <a href="#status">Status</a>
          </nav>
        )}

        <div className="nav-actions">
          <button className="theme-toggle-btn" onClick={onToggleTheme} title="Toggle theme" aria-label="Toggle theme">
            {theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}
          </button>

          {currentUser ? (
            <div className="user-menu">
              <button 
                className="user-greeting" 
                onClick={onOpenProfile}
                title="Open profile settings"
              >
                <UserCircle size={17} />
                <span>{currentUser.full_name}</span>
                <Settings size={14} />
              </button>
              <button className="btn-secondary nav-logout" onClick={onLogout} title="Sign out">
                <LogOut size={15} />
                <span>Sign out</span>
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
