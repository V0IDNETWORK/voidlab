import { create } from "zustand";
import { api, tokenStore } from "@/lib/api";
import type { Profile } from "@/types";

interface AuthState {
  profile: Profile | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  error: string | null;
  hydrate: () => Promise<void>;
  login: (username: string, password: string) => Promise<void>;
  register: (data: { username: string; email: string; password: string; password_confirm: string; display_name: string }) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  profile: null,
  isLoading: true,
  isAuthenticated: false,
  error: null,

  hydrate: async () => {
    if (!tokenStore.getAccess()) {
      set({ isLoading: false });
      return;
    }
    try {
      const { data } = await api.get<Profile>("/accounts/me/");
      set({ profile: data, isAuthenticated: true, isLoading: false });
    } catch {
      tokenStore.clear();
      set({ profile: null, isAuthenticated: false, isLoading: false });
    }
  },

  login: async (username, password) => {
    set({ error: null });
    try {
      const { data } = await api.post("/accounts/login/", { username, password });
      tokenStore.set(data.access, data.refresh);
      await get().hydrate();
    } catch {
      set({ error: "Invalid username or password." });
      throw new Error("login_failed");
    }
  },

  register: async (payload) => {
    set({ error: null });
    try {
      await api.post("/accounts/register/", payload);
      await get().login(payload.username, payload.password);
    } catch (err: any) {
      const detail = err?.response?.data?.error?.detail;
      const message = detail ? Object.values(detail).flat().join(" ") : "Registration failed.";
      set({ error: message });
      throw new Error("register_failed");
    }
  },

  logout: () => {
    tokenStore.clear();
    set({ profile: null, isAuthenticated: false });
  },
}));
