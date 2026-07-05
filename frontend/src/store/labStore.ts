import { create } from "zustand";
import { api } from "@/lib/api";
import type { Category, LabSummary } from "@/types";

interface LabState {
  categories: Category[];
  labs: LabSummary[];
  isLoading: boolean;
  fetchAll: () => Promise<void>;
}

function unwrap<T>(data: { results: T[] } | T[]): T[] {
  return Array.isArray(data) ? data : data.results;
}

export const useLabStore = create<LabState>((set) => ({
  categories: [],
  labs: [],
  isLoading: false,

  fetchAll: async () => {
    set({ isLoading: true });
    const [categoriesRes, labsRes] = await Promise.all([
      api.get<{ results: Category[] } | Category[]>("/labs/categories/"),
      api.get<{ results: LabSummary[] } | LabSummary[]>("/labs/"),
    ]);
    set({ categories: unwrap(categoriesRes.data), labs: unwrap(labsRes.data), isLoading: false });
  },
}));
