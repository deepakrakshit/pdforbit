'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import {
  ApiError,
  clearStoredSession,
  fetchCurrentUser,
  loadStoredSession,
  loginRequest,
  logoutRequest,
  persistSession,
  refreshRequest,
  signupRequest,
  type StoredSession,
  type UserProfile,
} from '@/lib/auth';

interface AuthContextValue {
  user: UserProfile | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<StoredSession | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const applyTokens = useCallback(async (accessToken: string, refreshToken: string) => {
    const user = await fetchCurrentUser(accessToken);
    const nextSession = { accessToken, refreshToken, user };
    persistSession(nextSession);
    setSession(nextSession);
  }, []);

  const refreshSession = useCallback(async (refreshToken: string) => {
    const tokens = await refreshRequest(refreshToken);
    await applyTokens(tokens.access_token, tokens.refresh_token);
  }, [applyTokens]);

  useEffect(() => {
    let cancelled = false;

    async function hydrate(): Promise<void> {
      const stored = loadStoredSession();
      if (!stored) {
        if (!cancelled) {
          setIsLoading(false);
        }
        return;
      }

      try {
        const user = await fetchCurrentUser(stored.accessToken);
        if (cancelled) {
          return;
        }
        const nextSession = { ...stored, user };
        persistSession(nextSession);
        setSession(nextSession);
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          try {
            await refreshSession(stored.refreshToken);
          } catch {
            clearStoredSession();
            if (!cancelled) {
              setSession(null);
            }
          }
        } else {
          clearStoredSession();
          if (!cancelled) {
            setSession(null);
          }
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void hydrate();
    return () => {
      cancelled = true;
    };
  }, [refreshSession]);

  const login = useCallback(async (email: string, password: string) => {
    const tokens = await loginRequest(email, password);
    await applyTokens(tokens.access_token, tokens.refresh_token);
  }, [applyTokens]);

  const signup = useCallback(async (email: string, password: string) => {
    const tokens = await signupRequest(email, password);
    await applyTokens(tokens.access_token, tokens.refresh_token);
  }, [applyTokens]);

  const logout = useCallback(async () => {
    const refreshToken = session?.refreshToken;
    clearStoredSession();
    setSession(null);
    if (!refreshToken) {
      return;
    }

    try {
      await logoutRequest(refreshToken);
    } catch {
      // Local logout should still succeed even if the network call fails.
    }
  }, [session?.refreshToken]);

  const refreshUser = useCallback(async () => {
    if (!session) {
      return;
    }

    try {
      const user = await fetchCurrentUser(session.accessToken);
      const nextSession = { ...session, user };
      persistSession(nextSession);
      setSession(nextSession);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        await refreshSession(session.refreshToken);
        return;
      }
      throw error;
    }
  }, [refreshSession, session]);

  const value = useMemo<AuthContextValue>(() => ({
    user: session?.user ?? null,
    accessToken: session?.accessToken ?? null,
    isAuthenticated: Boolean(session?.accessToken),
    isLoading,
    login,
    signup,
    logout,
    refreshUser,
  }), [isLoading, login, logout, refreshUser, session, signup]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}