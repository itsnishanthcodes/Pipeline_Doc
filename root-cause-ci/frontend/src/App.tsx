import { useEffect, useState } from 'react';
import { AuthModal } from './components/AuthModal';
import { DashboardWorkspace } from './components/DashboardWorkspace';
import { EvaluationMetrics } from './components/EvaluationMetrics';
import { HeroSection } from './components/HeroSection';
import { MethodologyFlow } from './components/MethodologyFlow';
import { Navbar } from './components/Navbar';
import { ProblemObjectives } from './components/ProblemObjectives';
import { ProfileModal } from './components/ProfileModal';
import { TeamFooter } from './components/TeamFooter';
import { fetchHealth } from './services/api';
import { clearAuthSession, fetchProfile, getAuthToken, getStoredAuthUser, saveAuthUser } from './services/authApi';
import type { UserAuthData } from './services/authApi';
import type { HealthResponse } from './types/health';

function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [scrollY, setScrollY] = useState(0);

  // Theme toggle state
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');

  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState<'login' | 'register'>('register');
  const [profileOpen, setProfileOpen] = useState(false);
  const [currentUser, setCurrentUser] = useState<UserAuthData | null>(() => getStoredAuthUser());
  const [authLoading, setAuthLoading] = useState(() => Boolean(getAuthToken()));

  useEffect(() => {
    const token = getAuthToken();
    if (!token) {
      setAuthLoading(false);
      return;
    }

    fetchProfile(token)
      .then((user) => {
        saveAuthUser(user);
        setCurrentUser(user);
      })
      .catch(() => {
        clearAuthSession();
        setCurrentUser(null);
      })
      .finally(() => setAuthLoading(false));
  }, []);

  useEffect(() => {
    // Set theme on root HTML element
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch((reason: unknown) => {
        setHealthError(reason instanceof Error ? reason.message : 'Failed to connect to backend health API');
      });

    const handleScroll = () => {
      setScrollY(window.scrollY);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  const handleOpenAuth = (mode: 'login' | 'register') => {
    setAuthMode(mode);
    setAuthOpen(true);
  };

  const handleLogout = () => {
    clearAuthSession();
    setCurrentUser(null);
    setAuthLoading(false);
    setProfileOpen(false);
  };

  return (
    <div className="main-wrapper">
      <Navbar
        onOpenAuth={handleOpenAuth}
        currentUser={currentUser}
        onLogout={handleLogout}
        onOpenProfile={() => setProfileOpen(true)}
        theme={theme}
        onToggleTheme={toggleTheme}
      />

      <main>
        {authLoading && !currentUser ? (
          <div className="auth-loading-screen" role="status">Restoring your dashboard...</div>
        ) : currentUser ? (
          /* Render Authenticated Developer Workspace when Logged In */
          <DashboardWorkspace
            user={currentUser}
            onLogout={handleLogout}
            onOpenProfile={() => setProfileOpen(true)}
          />
        ) : (
          /* Render Landing Page & Project Showcase when Logged Out */
          <>
            <HeroSection
              onGetStarted={() => handleOpenAuth('register')}
              scrollY={scrollY}
            />
            <ProblemObjectives />
            <MethodologyFlow />
            <EvaluationMetrics health={health} error={healthError} />
          </>
        )}
      </main>

      <TeamFooter />

      <AuthModal
        isOpen={authOpen}
        onClose={() => setAuthOpen(false)}
        onSuccess={(user) => setCurrentUser(user)}
        initialMode={authMode}
      />

      {currentUser && (
        <ProfileModal
          isOpen={profileOpen}
          onClose={() => setProfileOpen(false)}
          currentUser={currentUser}
          onUpdateUser={(updated) => setCurrentUser(updated)}
        />
      )}
    </div>
  );
}

export default App;
