'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';
import { useRouter } from 'next/navigation';
import { authApi } from '@/lib/api';
import { saveAuth, clearAuth, getToken, getUser, isTokenExpired } from '@/lib/auth';
import type { UserProfile, UserCreate, UserLogin } from '@/types/api';

interface AuthState {
  user: UserProfile | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

interface AuthActions {
  login: (data: UserLogin) => Promise<void>;
  register: (data: UserCreate) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState & AuthActions | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Rehydrate from localStorage on mount
  useEffect(() => {
    const token = getToken();
    const stored = getUser();
    if (token && stored && !isTokenExpired(token)) {
      setUser(stored);
    } else {
      clearAuth();
    }
    setIsLoading(false);
  }, []);

  const login = useCallback(async (data: UserLogin) => {
    const res = await authApi.login(data);
    saveAuth(res.access_token, res.user);
    setUser(res.user);
    router.push('/chat');
  }, [router]);

  const register = useCallback(async (data: UserCreate) => {
    const res = await authApi.register(data);
    saveAuth(res.access_token, res.user);
    setUser(res.user);
    router.push('/chat');
  }, [router]);

  const logout = useCallback(() => {
    clearAuth();
    setUser(null);
    router.push('/login');
  }, [router]);

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: user !== null,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuthContext() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuthContext must be used within AuthProvider');
  return ctx;
}
