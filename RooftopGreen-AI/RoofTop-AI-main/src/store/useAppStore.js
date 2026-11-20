import { create } from 'zustand'
import { persist } from 'zustand/middleware'

const STORE_PERSIST_KEY = 'rooftopgreen-v1'

const initialWorkflowState = {
  preferences: null,
  budget: 15000,
  selectedPlants: [],
  roofDimensions: { width_ft: 20, depth_ft: 15, bearing: 180, grid_ft: 2 },
  // roofPhotos: railingPts are normalized {x: 0..1, y: 0..1} coordinates relative to natural photo dimensions
  roofPhotos: [
    { file: null, url: null, name: '', photoId: null, railingPts: [], markedZones: [] },
    { file: null, url: null, name: '', photoId: null, railingPts: [], markedZones: [] },
    { file: null, url: null, name: '', photoId: null, railingPts: [], markedZones: [] },
    { file: null, url: null, name: '', photoId: null, railingPts: [], markedZones: [] },
  ],
  activePhotoIdx: 0,
  lighting: 'daylight',
  roofCorners: null,
  roofArea: null,
  roofAreaSqFt: null,
  gridCells: null,
  grid: null,
  structuralGrid: null,
  obstacles: [],
  detectedObstacles: [],
  sunlightZones: { mode: 'MIXED', pins: [] },
  selectedVariant: 'Balanced',
  selectedLayout: 'Balanced',
  gardenLayouts: null,
  visualizationsByIndex: {},
  visualizations: null,
  bom: null,
  structuralLoad: null,
  cart: [],
  orders: [],
  symptoms: [],
  doctorResult: null,
  plan: null,
  onboarding: {},
  currentStep: 1,
  isLoading: false,
  error: null,
  sessionId: null,
}

const useAppStore = create(
  persist(
    (set, get) => ({
      // ── Auth ──────────────────────────────────────────────
      user: { name: 'Demo User', email: 'demo@rooftopgreen.ai' },
      isAuthenticated: true,
      sessionId: null,

      login: ({ email, name }) => {
        const storedUser = typeof window !== 'undefined' ? window.localStorage?.getItem('rooftopgreen_last_user') : null
        const currentIdentifier = (email || name || '').trim().toLowerCase()

        // If newly logged in user does not match previously stored user, start with a 100% clean slate
        if (!storedUser || (currentIdentifier && storedUser.toLowerCase() !== currentIdentifier)) {
          get().resetWorkflowState(true)
        }

        const derivedName = name || (email ? email.split('@')[0].replace(/[._-]/g, ' ') : 'User')
        const formattedName = derivedName ? derivedName.charAt(0).toUpperCase() + derivedName.slice(1) : 'User'
        set({ isAuthenticated: true, user: { name: formattedName, email: email || '' } })

        try {
          if (typeof window !== 'undefined' && window.localStorage) {
            window.localStorage.setItem('rooftopgreen_last_user', currentIdentifier || formattedName.toLowerCase())
          }
        } catch (e) {}
      },
      signup: ({ name, email }) => {
        // A newly registered account always starts with a 100% clean slate
        get().resetWorkflowState(true)
        const currentIdentifier = (email || name || '').trim().toLowerCase()
        const formattedName = name?.trim() || 'User'
        set({
          isAuthenticated: true,
          user: { name: formattedName, email: email?.trim() || '' }
        })
        try {
          if (typeof window !== 'undefined' && window.localStorage) {
            window.localStorage.setItem('rooftopgreen_last_user', currentIdentifier || formattedName.toLowerCase())
          }
        } catch (e) {}
      },
      logout: () => {
        get().resetWorkflowState(false)
        set({ isAuthenticated: false, user: null, sessionId: null, currentStep: 1 })
        try {
          if (typeof window !== 'undefined') {
            window.localStorage?.removeItem(STORE_PERSIST_KEY)
            window.localStorage?.removeItem('rooftopgreen_last_user')
            window.sessionStorage?.clear()
          }
        } catch (e) {}
      },
      setSessionId: (id) => set({ sessionId: id }),

      // ── Step 1 – Preferences & Crops ──────────────────────
      preferences: null,
      budget: 15000,
      selectedPlants: [],
      setBudget: (b) => set((state) => {
        const num = Number(b) || 0
        return {
          budget: num,
          preferences: state.preferences
            ? { ...state.preferences, budget: num, budget_bdt: num }
            : { budget: num, budget_bdt: num }
        }
      }),
      savePreferences: (prefs) => set((state) => {
        const plants = prefs?.preferred_plants || prefs?.selected_plants || prefs?.selectedPlants || state.selectedPlants || []
        const budget = Number(prefs?.budget ?? prefs?.budget_bdt ?? state.budget ?? 15000)
        return {
          preferences: { ...prefs, budget, budget_bdt: budget },
          budget,
          selectedPlants: plants
        }
      }),
      setSelectedPlants: (plants) => set((state) => ({
        selectedPlants: plants,
        preferences: state.preferences ? { ...state.preferences, preferred_plants: plants } : { preferred_plants: plants }
      })),

      // ── Step 2 – Roof ────────────────────────────────────
      roofDimensions: { width_ft: 20, depth_ft: 15, bearing: 180, grid_ft: 2 },
      setRoofDimensions: (dims) => set({ roofDimensions: { ...get().roofDimensions, ...dims } }),

      // roofPhotos: railingPts are normalized {x: 0..1, y: 0..1} coordinates relative to natural photo dimensions
      roofPhotos: [
        { file: null, url: null, name: '', photoId: null, railingPts: [], markedZones: [] },
        { file: null, url: null, name: '', photoId: null, railingPts: [], markedZones: [] },
        { file: null, url: null, name: '', photoId: null, railingPts: [], markedZones: [] },
        { file: null, url: null, name: '', photoId: null, railingPts: [], markedZones: [] },
      ],
      activePhotoIdx: 0,
      setRoofPhotos: (photos) => set({ roofPhotos: photos }),
      setActivePhotoIdx: (idx) => set({ activePhotoIdx: idx }),
      lighting: 'daylight',
      setLighting: (l) => set({ lighting: l }),

      roofCorners: null,
      setRoofCorners: (corners) => set({ roofCorners: corners }),

      roofArea: null,
      roofAreaSqFt: null,
      setRoofArea: (area) => set({ roofArea: area, roofAreaSqFt: area }),
      setRoofAreaSqFt: (area) => set({ roofAreaSqFt: area, roofArea: area }),

      // gridCells / structuralGrid / grid: { "A1": { sunlight:"FULL_SUN", zone:"GARDENING", row:0, col:0 }, ... }
      gridCells: null,
      grid: null,
      structuralGrid: null,
      setGridCells: (cells) => set({ gridCells: cells, grid: cells, structuralGrid: cells }),
      setGrid: (cells) => set({ gridCells: cells, grid: cells, structuralGrid: cells }),
      setStructuralGrid: (cells) => set({ structuralGrid: cells, gridCells: cells, grid: cells }),
      updateCell: (cellId, updates) => set((state) => {
        const nextCells = { ...state.gridCells, [cellId]: { ...state.gridCells?.[cellId], ...updates } }
        return { gridCells: nextCells, grid: nextCells, structuralGrid: nextCells }
      }),

      obstacles: [],
      setObstacles: (obs) => set({ obstacles: obs }),
      detectedObstacles: [],
      setDetectedObstacles: (obs) => set({ detectedObstacles: obs }),
      confirmObstacle: (id) => set((state) => ({
        obstacles: [...state.obstacles, state.detectedObstacles.find(o => o.id === id)].filter(Boolean),
        detectedObstacles: state.detectedObstacles.filter(o => o.id !== id)
      })),
      removeObstacle: (id) => set((state) => ({ obstacles: state.obstacles.filter(o => o.id !== id) })),

      // ── Step 2 Sunlight Micro-Climate Zones ──────────────
      sunlightZones: { mode: 'MIXED', pins: [] }, // mode: 'FULL_SUN' | 'PARTIAL_SHADE' | 'MIXED'
      setSunlightZones: (zones) => set((state) => ({
        sunlightZones: typeof zones === 'function'
          ? zones(state.sunlightZones)
          : { ...state.sunlightZones, ...(typeof zones === 'object' && zones !== null ? zones : { mode: zones }) }
      })),

      // ── Step 3 – Garden Design ───────────────────────────
      selectedVariant: 'Balanced',
      selectedLayout: 'Balanced',
      setSelectedVariant: (v) => set({ selectedVariant: v, selectedLayout: v }),
      setSelectedLayout: (v) => set({ selectedVariant: v, selectedLayout: v }),

      gardenLayouts: null,  // { Productive: {...}, Colorful: {...}, Balanced: {...} }
      setGardenLayouts: (layouts) => set({ gardenLayouts: layouts }),

      visualizationsByIndex: {}, // { [photoIdx]: { status, preview_data_url, image_url, ... } }
      visualizations: null,
      setVisualizationForIndex: (idx, data) => set((state) => ({
        visualizationsByIndex: {
          ...state.visualizationsByIndex,
          [idx]: data,
        },
        visualizations: {
          ...state.visualizationsByIndex,
          [idx]: data,
        }
      })),
      setVisualizations: (vis) => set({ visualizations: vis, visualizationsByIndex: vis || {} }),
      clearVisualizations: () => set({ visualizationsByIndex: {}, visualizations: null }),
      clearVisualizationForIndex: (idx) => set((s) => {
        const next = { ...s.visualizationsByIndex }
        delete next[idx]
        return { visualizationsByIndex: next, visualizations: next }
      }),

      // ── Step 4 – Materials ───────────────────────────────
      bom: null,
      setBom: (bom) => set({ bom }),
      structuralLoad: null,
      setStructuralLoad: (load) => set({ structuralLoad: load }),

      // ── Step 5 – Marketplace ─────────────────────────────
      cart: [],
      addToCart: (item) => set((state) => {
        const existing = state.cart.find(c => c.product_id === item.product_id)
        if (existing) return { cart: state.cart.map(c => c.product_id === item.product_id ? { ...c, qty: c.qty + (item.qty || 1) } : c) }
        return { cart: [...state.cart, { ...item, qty: item.qty || 1 }] }
      }),
      removeFromCart: (product_id) => set((state) => ({ cart: state.cart.filter(c => c.product_id !== product_id) })),
      clearCart: () => set({ cart: [] }),
      addRecommendedToCart: (customItems) => set((state) => {
        const sourceItems = (customItems && Array.isArray(customItems) && customItems.length > 0)
          ? customItems
          : (state.bom?.items || [])
        if (!sourceItems.length) return {}
        const newItems = sourceItems.map(item => {
          const name = item.description || item.item || item.name || item.product_name || 'Rooftop Material'
          const qty = Math.max(1, Math.ceil(Number(item.qty ?? item.quantity ?? item.count ?? 1)))
          const unitPrice = Number(item.unit_price ?? item.unit_cost_bdt ?? item.price_bdt ?? item.price ?? 0)
          const unit = item.unit || item.price_unit || 'pcs'
          return {
            product_id: name,
            id: name,
            name,
            qty,
            unit_price_bdt: unitPrice,
            price_bdt: unitPrice,
            unit,
            supplier_id: 'sup1',
          }
        })
        const cartMap = new Map()
        for (const it of state.cart) {
          const key = it.product_id || it.id || it.name
          cartMap.set(key, { ...it })
        }
        for (const it of newItems) {
          const key = it.product_id || it.id || it.name
          if (cartMap.has(key)) {
            const existing = cartMap.get(key)
            existing.qty = (existing.qty || 1) + it.qty
          } else {
            cartMap.set(key, it)
          }
        }
        return { cart: Array.from(cartMap.values()) }
      }),

      orders: [],
      addOrder: (order) => set((state) => ({ orders: [...state.orders, order] })),

      // ── Step 6 – Plant Doctor ────────────────────────────
      symptoms: [],
      setSymptoms: (s) => set({ symptoms: s }),
      doctorResult: null,
      setDoctorResult: (r) => set({ doctorResult: r }),

      // ── UI State ─────────────────────────────────────────
      currentStep: 1,
      setCurrentStep: (step) => set({ currentStep: step }),
      isLoading: false,
      setLoading: (v) => set({ isLoading: v }),
      error: null,
      setError: (e) => set({ error: e }),

      onboarding: {},
      saveProfile: (profile) => set((state) => ({
        onboarding: profile,
        user: profile?.name ? { ...state.user, name: profile.name } : state.user
      })),
      plan: null,
      savePlan: (plan) => set({ plan }),

      // ── Workflow & Plan Full State Reset ──────────────────
      resetWorkflowState: (preserveUser = false) => {
        const nextState = {
          ...initialWorkflowState,
          roofPhotos: [
            { file: null, url: null, name: '', railingPts: [], markedZones: [] },
            { file: null, url: null, name: '', railingPts: [], markedZones: [] },
            { file: null, url: null, name: '', railingPts: [], markedZones: [] },
            { file: null, url: null, name: '', railingPts: [], markedZones: [] },
          ],
        }

        if (!preserveUser) {
          nextState.user = null
          nextState.isAuthenticated = false
        }

        set(nextState)

        try {
          if (typeof window !== 'undefined') {
            if (window.localStorage) {
              window.localStorage.removeItem(STORE_PERSIST_KEY)

              const keysToRemove = []
              for (let i = 0; i < window.localStorage.length; i++) {
                const k = window.localStorage.key(i)
                if (
                  k &&
                  (k.startsWith('rooftop_') ||
                   k.startsWith('garden_design_') ||
                   k.startsWith('viz_cache_') ||
                   k.startsWith('garden_plan_') ||
                   k.startsWith('rooftopgreen_cache_') ||
                   k.startsWith('roof_'))
                ) {
                  keysToRemove.push(k)
                }
              }
              keysToRemove.forEach(k => window.localStorage.removeItem(k))

              if (!preserveUser) {
                window.localStorage.removeItem('rooftopgreen_last_user')
              }
            }

            if (window.sessionStorage) {
              window.sessionStorage.clear()
            }
          }
        } catch (e) {
          console.warn('Could not clear cached storage keys:', e)
        }
      },

      resetAll: () => {
        get().resetWorkflowState(false)
      },

      resetPlan: () => {
        get().resetWorkflowState(true)
      },

      reset: () => {
        get().resetWorkflowState(false)
      },
    }),
    {
      name: STORE_PERSIST_KEY,
      version: 2,
      migrate: (persisted) => ({
        ...persisted,
        visualizationsByIndex: {},
        visualizations: null,
      }),
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
        sessionId: state.sessionId,
        preferences: state.preferences,
        budget: state.budget,
        selectedPlants: state.selectedPlants,
        roofDimensions: state.roofDimensions,
        roofArea: state.roofArea,
        roofAreaSqFt: state.roofAreaSqFt,
        gridCells: state.gridCells,
        structuralGrid: state.structuralGrid,
        selectedVariant: state.selectedVariant,
        sunlightZones: state.sunlightZones,
        cart: state.cart,
        currentStep: state.currentStep,
        onboarding: state.onboarding,
      }),
    }
  )
)

export { useAppStore }
export default useAppStore
