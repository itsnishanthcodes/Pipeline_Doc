import { useEffect, useState } from 'react';
import { AuthModal } from './components/AuthModal';
import { DashboardWorkspace } from './components/DashboardWorkspace';
import { EvaluationMetrics } from './components/EvaluationMetrics';
import { HeroSection } from './components/HeroSection';
import { MethodologyFlow } from './components/MethodologyFlow';
import { Navbar } from './components/Navbar';
import { ProblemObjectives } from './components/ProblemObjectives';
import { TeamFooter } from './components/TeamFooter';
import { fetchHealth } from './services/api';
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
  const [currentUser, setCurrentUser] = useState<UserAuthData | null>(null);

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

  return (
    <div className="main-wrapper">
      <Navbar
        onOpenAuth={handleOpenAuth}
        currentUser={currentUser}
        onLogout={() => setCurrentUser(null)}
        theme={theme}
        onToggleTheme={toggleTheme}
      />

      <main>
        {currentUser ? (
          /* Render Authenticated Developer Workspace when Logged In */
          <DashboardWorkspace
            user={currentUser}
            onLogout={() => setCurrentUser(null)}
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
    </div>
  );
}

export default App;
