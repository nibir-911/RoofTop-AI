import { create } from 'zustand'

const defaultUser = {
  name: 'Aisha Patel',
  email: 'aisha@rooftopai.com',
}

export const useAppStore = create((set) => ({
  user: defaultUser,
  isAuthenticated: true,
  onboarding: {},
  plan: null,

  login: ({ email, name }) =>
    set({
      isAuthenticated: true,
      user: {
        name: name || 'Garden Manager',
        email,
      },
    }),

  signup: ({ name, email }) =>
    set({
      isAuthenticated: true,
      user: { name, email },
    }),

  logout: () => set({ isAuthenticated: false, user: null, onboarding: {}, plan: null }),

  saveProfile: (profile) => set({ onboarding: profile }),
  savePlan: (plan) => set({ plan }),
}))
