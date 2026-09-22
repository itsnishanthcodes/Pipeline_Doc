const baseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

const TOKEN_KEY = 'access_token';

export function saveAuthSession(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function saveAuthUser(user: UserAuthData): void {
  localStorage.setItem('auth_user', JSON.stringify(user));
}

export function clearAuthSession(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem('auth_user');
}

export function getAuthToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredAuthUser(): UserAuthData | null {
  try {
    const storedUser = localStorage.getItem('auth_user');
    return storedUser ? (JSON.parse(storedUser) as UserAuthData) : null;
  } catch {
    return null;
  }
}

export interface UserAuthData {
  id: number;
  full_name: string;
  email: string;
  github_username?: string;
  github_token?: string;
  role: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: UserAuthData;
}

export interface ProfileUpdatePayload {
  full_name?: string;
  github_username?: string;
  github_token?: string;
  current_password?: string;
  new_password?: string;
  role?: string;
}

export async function registerUser(payload: {
  full_name: string;
  email: string;
  password: string;
  github_username?: string;
  github_token?: string;
  role: string;
}): Promise<AuthResponse> {
  const res = await fetch(`${baseUrl}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Registration failed' }));
    throw new Error(err.detail || 'Registration failed');
  }

  return res.json();
}

export async function loginUser(payload: {
  email: string;
  password: string;
}): Promise<AuthResponse> {
  const res = await fetch(`${baseUrl}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Login failed' }));
    throw new Error(err.detail || 'Invalid email or password');
  }

  return res.json();
}

export async function fetchProfile(token: string): Promise<UserAuthData> {
  const res = await fetch(`${baseUrl}/auth/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to fetch profile' }));
    throw new Error(err.detail || 'Failed to fetch profile');
  }

  return res.json();
}

export async function updateProfile(token: string, payload: ProfileUpdatePayload): Promise<UserAuthData> {
  const res = await fetch(`${baseUrl}/auth/me`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to update profile' }));
    throw new Error(err.detail || 'Failed to update profile');
  }

  return res.json();
}

export interface GitHubVerifyResponse {
  valid: boolean;
  message: string;
  avatar_url?: string;
}

export async function verifyGitHubCredentials(github_username?: string, github_token?: string): Promise<GitHubVerifyResponse> {
  const res = await fetch(`${baseUrl}/auth/verify-github`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ github_username, github_token }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'GitHub verification failed' }));
    throw new Error(err.detail || 'GitHub verification failed');
  }

  return res.json();
}
