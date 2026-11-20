import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || '/api'

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// Mock data for standalone (no-backend) mode
export const MOCK_SESSION_ID = 'demo-session-' + Math.random().toString(36).slice(2, 8)

export const isMockMode = () => {
  return localStorage.getItem('rooftopgreen-mock') === 'true'
}

// Helper: try real API, fall back to mock data
export const withFallback = async (apiFn, mockData) => {
  try {
    const res = await apiFn()
    return res.data
  } catch (e) {
    if (e.code === 'ERR_NETWORK' || e.message?.includes('Network Error') || e.code === 'ECONNREFUSED') {
      console.warn('Backend not available, using mock data')
      return typeof mockData === 'function' ? mockData() : mockData
    }
    throw e
  }
}

export const savePreferences = (data) => api.post('/preferences', data)
export const uploadRoofPhoto = (edgeId, file) => {
  const fd = new FormData(); fd.append('file', file); fd.append('edge_id', edgeId)
  return api.post('/roof/upload', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
}
export const analyzeRoof = (data) => api.post('/roof/analyze', data)
export const calculateArea = (data) => api.post('/roof/area', data)
export const generateGrid = (data) => api.post('/roof/grid', data)
export const saveCellConditions = (data) => api.post('/roof/cells/conditions', data)
export const saveObstacles = (data) => api.post('/roof/obstacles', data)
export const recommendPlants = (data) => api.post('/garden/recommend', data)
export const generateLayout = (data) => api.post('/garden/layout', data)
export const calculateMaterials = (data) => api.post('/garden/materials', data)
export const getExplanation = (data) => api.post('/garden/explain', data)
export const getPlants = () => api.get('/plants')
export const getGuide = (plantId) => api.get(`/guides/${plantId}`)
export const getSuppliers = () => api.get('/suppliers')
export const getProducts = () => api.get('/products')
export const getMarketplace = () => api.get('/marketplace')
export const createOrder = (data) => api.post('/orders', data)
export const getOrder = (orderId) => api.get(`/orders/${orderId}`)
export const simulateWebhook = (orderId, data) => api.post(`/orders/${orderId}/webhook`, data)
export const analyzePlantDoctor = (data) => api.post('/plant-doctor/analyze', data)
export const chatPlantDoctor = (data) => api.post('/plant-doctor/chat', data, { timeout: 45000 })
export const detectRoof = (data) => api.post('/detect-roof', data, { timeout: 45000 })
export const detectRoofGrid = (data) => api.post('/detect-roof-grid', data, { timeout: 45000 })
export const analyzeRoofPhoto = (data) => api.post('/analyze-roof', data, { timeout: 45000 })
export const generateDesign = (data) => api.post('/generate-design', data, {
  timeout: 180000,
})
export const visualizeRooftop = (formData) => api.post('/roof/visualize', formData, {
  headers: { 'Content-Type': 'multipart/form-data' },
  timeout: 180000,
})

// Mock responses for demo mode
export const MOCK = {
  preferences: { session_id: MOCK_SESSION_ID, status: 'ok' },
  grid: (w, d, g=2) => {
    const cells = {}
    const cols = Math.ceil(w/g), rows = Math.ceil(d/g)
    for (let r=0; r<rows; r++) for (let c=0; c<cols; c++) {
      const id = String.fromCharCode(65+c) + (r+1)
      cells[id] = { sunlight: 'FULL_SUN', zone: 'GARDENING', row: r, col: c,
        x0: c*g, y0: r*g, x1: Math.min((c+1)*g,w), y1: Math.min((r+1)*g,d),
        area_sqft: (Math.min((c+1)*g,w)-c*g)*(Math.min((r+1)*g,d)-r*g) }
    }
    return { cells, rows, cols, width_ft: w, depth_ft: d, grid_ft: g }
  },
  layout: { Productive: { placements: [], notes: ['Demo mode'], scene_json: null },
            Colorful: { placements: [], notes: ['Demo mode'], scene_json: null },
            Balanced: { placements: [], notes: ['Demo mode'], scene_json: null } },
  materials: { items: [
    { name: 'Planter box 2×2 ft', qty: 10, unit: 'piece', unit_cost_bdt: 500, total_bdt: 5000 },
    { name: 'Light soil mix', qty: 150, unit: 'litre', unit_cost_bdt: 9, total_bdt: 1350 },
  ], subtotal_bdt: 6350, labour_bdt: 952, total_bdt: 7302,
     structural_load: { avg_kg_m2: 45, peak_kg_m2: 80, disclaimer: 'STRUCTURAL SAFETY DISCLAIMER: These are estimated wet-load figures only. A qualified structural engineer must verify your rooftop actual load capacity before installation.' }},
  suppliers: [
    { id: 'sup1', name: 'Dhaka Nursery House', category: 'Nursery', area: 'Mirpur', verified: true },
    { id: 'sup2', name: 'Mita Pot & Planter', category: 'Pots', area: 'Gulshan', verified: true },
    { id: 'sup3', name: 'GreenSoil BD', category: 'Soil', area: 'Mohammadpur', verified: true },
    { id: 'sup4', name: 'Garden Tools BD', category: 'Tools', area: 'Dhanmondi', verified: true },
  ],
  doctorResult: {
    primary_cause: 'Nitrogen deficiency (suspected)', confidence_pct: 65, confidence_label: 'Medium',
    alternative_causes: ['Iron deficiency', 'Natural aging'],
    follow_up_questions: ['Are lower leaves yellowing first?', 'Do you water daily?'],
    care_steps: ['Apply balanced NPK fertilizer', 'Reduce watering frequency', 'Check soil drainage'],
    disclaimer: 'This is preliminary guidance only. Consult a certified agronomist for diagnosis.'
  }
}

export default api
