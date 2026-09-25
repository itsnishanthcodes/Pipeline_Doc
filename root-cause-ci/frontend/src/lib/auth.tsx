import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { api, session, SESSION_EXPIRED_EVENT } from './api';
import type { TokenResponse, User } from '../types/api';

interface AuthState {
  user: User | null;
  status: 'loading' | 'signed-in' | 'signed-out';
  expired: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  register: (body: Parameters<typeof api.register>[0]) => Promise<void>;
  signOut: () => void;
  setUser: (user: User) => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<AuthState['status']>(session.get() ? 'loading' : 'signed-out');
  const [expired, setExpired] = useState(false);

  // Restore the session after a page refresh.
  useEffect(() => {
    if (!session.get()) return;
    api.me()
      .then((u) => {
        setUser(u);
        setStatus('signed-in');
      })
      .catch(() => {
        session.clear();
        setStatus('signed-out');
      });
  }, []);

  useEffect(() => {
    const onExpired = () => {
      setUser(null);
      setStatus('signed-out');
      setExpired(true);
    };
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired);
  }, []);

  const accept = useCallback((res: TokenResponse) => {
    session.set(res.access_token);
    setUser(res.user);
    setStatus('signed-in');
    setExpired(false);
  }, []);

  const value = useMemo<AuthState>(() => ({
    user,
    status,
    expired,
    signIn: async (email, password) => accept(await api.login(email, password)),
    register: async (body) => accept(await api.register(body)),
    signOut: () => {
      session.clear();
      setUser(null);
      setStatus('signed-out');
    },
    setUser,
  }), [user, status, expired, accept]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
