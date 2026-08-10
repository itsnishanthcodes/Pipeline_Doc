const baseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export interface UserAuthData {
  id: number;
  full_name: string;
  email: string;
  github_username?: string;
  role: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UserAuthData;
}

export async function registerUser(payload: {
  full_name: string;
  email: string;
  password: str;
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
  password: str;
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
