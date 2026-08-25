// src/store/authStore.ts — Zustand auth state

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { User, AuthTokens } from "@/types";
import { tokenStorage } from "@/lib/api/client";
import { authApi } from "@/lib/api/endpoints";

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, password_confirm: string) => Promise<void>;
  logout: () => Promise<void>;
  fetchMe: () => Promise<void>;
  clearError: () => void;
  setUser: (user: User) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (email, password) => {
        set({ isLoading: true, error: null });
        try {
          const res = await authApi.login({ email, password });
          const data = res.data.data!;
          tokenStorage.set(data.access_token, data.refresh_token);
          set({ user: data.user, isAuthenticated: true, isLoading: false });
        } catch (err: any) {
          const message = err.response?.data?.error?.message || "Login failed.";
          set({ error: message, isLoading: false });
          throw err;
        }
      },

      register: async (email, password, password_confirm) => {
        set({ isLoading: true, error: null });
        try {
          const res = await authApi.register({ email, password, password_confirm });
          const data = res.data.data!;
          tokenStorage.set(data.access_token, data.refresh_token);
          set({ user: data.user, isAuthenticated: true, isLoading: false });
        } catch (err: any) {
          const message = err.response?.data?.error?.message || "Registration failed.";
          set({ error: message, isLoading: false });
          throw err;
        }
      },

      logout: async () => {
        const refreshToken = tokenStorage.getRefresh();
        try {
          if (refreshToken) {
            await authApi.logout(refreshToken);
          }
        } catch {
          // Ignore logout errors
        } finally {
          tokenStorage.clear();
          set({ user: null, isAuthenticated: false });
        }
      },

      fetchMe: async () => {
        try {
          const res = await authApi.me();
          set({ user: res.data.data!, isAuthenticated: true });
        } catch {
          tokenStorage.clear();
          set({ user: null, isAuthenticated: false });
        }
      },

      setUser: (user) => set({ user }),
      clearError: () => set({ error: null }),
    }),
    {
      name: "govscheme-auth",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
