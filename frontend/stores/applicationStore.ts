import { create } from "zustand";
import { Application } from "@/lib/api";

interface ApplicationStore {
  applications: Application[];
  loading: boolean;
  selectedId: string | null;

  setApplications: (apps: Application[]) => void;
  addApplication: (app: Application) => void;
  updateApplication: (id: string, updates: Partial<Application>) => void;
  removeApplication: (id: string) => void;
  setLoading: (v: boolean) => void;
  setSelectedId: (id: string | null) => void;

  // Derived
  getByStage: (stage: string) => Application[];
  getActive: () => Application[];
}

export const useApplicationStore = create<ApplicationStore>((set, get) => ({
  applications: [],
  loading: false,
  selectedId: null,

  setApplications: (applications) => set({ applications }),

  addApplication: (app) =>
    set((state) => ({ applications: [app, ...state.applications] })),

  updateApplication: (id, updates) =>
    set((state) => ({
      applications: state.applications.map((a) =>
        a.id === id ? { ...a, ...updates } : a
      ),
    })),

  removeApplication: (id) =>
    set((state) => ({
      applications: state.applications.filter((a) => a.id !== id),
    })),

  setLoading: (loading) => set({ loading }),
  setSelectedId: (selectedId) => set({ selectedId }),

  getByStage: (stage) => get().applications.filter((a) => a.stage === stage),

  getActive: () =>
    get().applications.filter(
      (a) => !["rejected", "ghosted", "withdrawn"].includes(a.stage)
    ),
}));
