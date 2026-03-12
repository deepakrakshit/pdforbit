export interface UserProfile {
  id: string;
  email: string;
  plan_type: 'free' | 'pro' | 'enterprise';
  subscription_status: 'inactive' | 'active' | 'cancelled' | 'expired';
  subscription_interval: 'monthly' | 'yearly' | null;
  subscription_started_at: string | null;
  subscription_expires_at: string | null;
  is_admin: boolean;
  credits_remaining: number;
  credit_limit: number;
  jobs_processed: number;
  created_at: string;
  last_credit_refresh: string;
}

interface AuthTokenResponse {
  access_token: string;
  refresh_token: string;
}

export interface StoredSession {
  accessToken: string;
  refreshToken: string;
  user: UserProfile;
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? '';
const STORAGE_KEY = 'pdforbit.auth.session';

function isBrowser(): boolean {
  return typeof window !== 'undefined';
}

function readErrorMessage(payload: unknown, fallback: string): string {
  if (typeof payload === 'string' && payload.trim()) {
    return payload;
  }

  if (payload && typeof payload === 'object') {
    const detail = (payload as { detail?: unknown }).detail;
    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: string } | undefined;
      if (first?.msg) {
        return first.msg;
      }
    }
    const message = (payload as { message?: unknown }).message;
    if (typeof message === 'string' && message.trim()) {
      return message;
    }
  }

  return fallback;
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    throw new ApiError(readErrorMessage(errorBody, `Request failed (${response.status})`), response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export function loadStoredSession(): StoredSession | null {
  if (!isBrowser()) {
    return null;
  }

  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as StoredSession;
  } catch {
    window.localStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

export function persistSession(session: StoredSession): void {
  if (!isBrowser()) {
    return;
  }
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
}

export function clearStoredSession(): void {
  if (!isBrowser()) {
    return;
  }
  window.localStorage.removeItem(STORAGE_KEY);
}

export function getAccessToken(): string | null {
  return loadStoredSession()?.accessToken ?? null;
}

export async function signupRequest(email: string, password: string): Promise<AuthTokenResponse> {
  return requestJson<AuthTokenResponse>('/api/v1/auth/signup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
}

export async function loginRequest(email: string, password: string): Promise<AuthTokenResponse> {
  return requestJson<AuthTokenResponse>('/api/v1/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
}

export async function refreshRequest(refreshToken: string): Promise<AuthTokenResponse> {
  return requestJson<AuthTokenResponse>('/api/v1/auth/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

export async function logoutRequest(refreshToken: string): Promise<void> {
  await requestJson<void>('/api/v1/auth/logout', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

export async function fetchCurrentUser(accessToken: string): Promise<UserProfile> {
  return requestJson<UserProfile>('/api/v1/users/me', {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}