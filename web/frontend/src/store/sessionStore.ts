import { create } from 'zustand';

interface SessionStore {
  currentSessionId: string | null;
  setCurrentSessionId: (id: string | null) => void;
}

export const useSessionStore = create<SessionStore>((set) => ({
  currentSessionId: null,
  setCurrentSessionId: (id) => set({ currentSessionId: id }),
}));
