import { useState, useEffect, useMemo } from 'react'
import { useAppStore } from '../store/useAppStore'
import { savePreferences, getPlants, withFallback } from '../services/api'
import { VERIFIED_50_PLANTS } from '../data/verified50Plants'
import {
  ChevronRight,
  ChevronLeft,
  Loader2,
  Search,
  X,
  Check,
  Leaf,
  ShieldCheck,
  Sparkles
} from 'lucide-react'

const GARDEN_TYPES = ['Container Garden', 'Terrace Garden', 'Open Rooftop', 'Covered Rooftop']
const PURPOSES = ['Grow Food', 'Decoration', 'Both']
const EXPERIENCE_LEVELS = ['Beginner', 'Intermediate', 'Expert']
const MAINTENANCE_OPTIONS = ['Daily', 'Weekends', 'Monthly']
const STYLE_OPTIONS = ['Productive', 'Colorful', 'Balanced', 'Mixed']
const WATER_OPTIONS = ['Municipal supply', 'Rainwater capture', 'Limited supply']

// 50 Verified Rooftop Agronomy Research Plants Immediate State (Zero Latency)
const FORMATTED_50_PLANTS = VERIFIED_50_PLANTS.map(p => {
  const rawEn = p.name_en || p.name || p.id || ''
  const cleanEn = rawEn.split('(')[0].trim().replace(/_/g, ' ')
  const bn = (p.name_bn || p.bangla_name || '').trim()
  const displayName = bn ? `${rawEn} (${bn})` : rawEn

  return {
    ...p,
    cleanEn,
    name_bn: bn,
    displayName,
    isVerified: Boolean(p.is_verified || p.verified)
  }
})

const defaultForm = {
  garden_type: 'Container Garden',
  purpose: 'Both',
  budget: 15000,
  experience: 'Beginner',
  maintenance: 'Weekends',
  style: 'Balanced',
  water_source: 'Municipal supply',
  preferred_plants: [],
}

export default function Preferences({ onNext, onBack }) {
  const { setSessionId, savePreferences: storeSavePreferences, preferences, budget: storeBudget, setBudget } = useAppStore()
  const [form, setForm] = useState(() => ({
    ...defaultForm,
    budget: Number(preferences?.budget ?? preferences?.budget_bdt ?? storeBudget ?? defaultForm.budget),
    ...(preferences || {}),
    preferred_plants: preferences?.preferred_plants || []
  }))

  const [plantsList, setPlantsList] = useState(FORMATTED_50_PLANTS)
  const [plantCategory, setPlantCategory] = useState('All Verified (50)')
  const [plantSearch, setPlantSearch] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // 1. Fetch plants from backend API (GET /api/plants)
  useEffect(() => {
    let isMounted = true

    const fetchPlantsData = async () => {
      try {
        const res = await withFallback(() => getPlants(), FORMATTED_50_PLANTS)
        if (!isMounted) return

        if (Array.isArray(res) && res.length > 0) {
          const formatted = res.map(p => {
            const rawEn = p.name_en || p.name || p.id || ''
            // Strip any parenthetical from English name to prevent double brackets
            const cleanEn = rawEn
              .split('(')[0]
              .trim()
              .replace(/_/g, ' ')
              .replace(/\b\w/g, c => c.toUpperCase())

            const bn = (p.name_bn || p.bangla_name || '').trim()
            const displayName = bn ? `${rawEn} (${bn})` : rawEn

            return {
              ...p,
              cleanEn,
              name_bn: bn,
              displayName,
              isVerified: Boolean(p.is_verified || p.verified)
            }
          })

          // Sort verified research plants first, then alphabetical
          formatted.sort((a, b) => {
            if (a.isVerified && !b.isVerified) return -1
            if (!a.isVerified && b.isVerified) return 1
            return a.cleanEn.localeCompare(b.cleanEn)
          })

          setPlantsList(formatted)
        } else {
          setPlantsList(FORMATTED_50_PLANTS)
        }
      } catch (err) {
        console.warn('Could not fetch plants from API, using verified 50 fallback', err)
        if (isMounted) {
          setPlantsList(FORMATTED_50_PLANTS)
        }
      }
    }

    fetchPlantsData()

    return () => {
      isMounted = false
    }
  }, [])

  // 2. Filtered plants based on category pill & search query
  const filteredPlants = useMemo(() => {
    return plantsList.filter(p => {
      // Search matching (English name, Bangla name, scientific name, or category)
      if (plantSearch.trim()) {
        const q = plantSearch.toLowerCase().trim()
        const matchEn = (p.cleanEn || '').toLowerCase().includes(q)
        const matchBn = (p.name_bn || '').includes(q)
        const matchSci = (p.scientific_name || '').toLowerCase().includes(q)
        const matchCat = (p.category || '').toLowerCase().includes(q)
        if (!matchEn && !matchBn && !matchSci && !matchCat) {
          return false
        }
      }

      // Category pill filter
      const cat = (p.category || '').toLowerCase()
      if (plantCategory === 'All Verified (50)' || plantCategory === 'All') {
        return plantSearch.trim() ? true : p.isVerified
      }
      if (plantCategory === 'Fruits') {
        return cat.includes('fruit') || cat.includes('shrub')
      }
      if (plantCategory === 'Vegetables') {
        return cat.includes('veg') || cat.includes('climb')
      }
      if (plantCategory === 'Leafy') {
        return cat.includes('leaf') || cat.includes('patch')
      }
      if (plantCategory === 'Flowers') {
        return cat.includes('flower') || cat.includes('bloom')
      }
      if (plantCategory === 'Herbs' || plantCategory === 'Herbs & Climbers') {
        return (
          cat.includes('herb') ||
          cat.includes('medicinal') ||
          cat.includes('climb') ||
          cat.includes('vine') ||
          p.cleanEn === 'Bottle Gourd' ||
          p.cleanEn === 'Bitter Gourd' ||
          p.cleanEn === 'Hyacinth Bean' ||
          p.cleanEn === 'Ridge Gourd'
        )
      }
      return true
    })
  }, [plantsList, plantCategory, plantSearch])

  // Multi-select helper: checks if plant is currently selected in form
  const isPlantSelected = (p) => {
    return (
      form.preferred_plants.includes(p.displayName) ||
      form.preferred_plants.includes(p.cleanEn) ||
      form.preferred_plants.includes(p.name_en) ||
      form.preferred_plants.includes(p.id)
    )
  }

  // Toggle selection on chip click
  const togglePlant = (p) => {
    const isSel = isPlantSelected(p)
    setForm(f => {
      if (isSel) {
        return {
          ...f,
          preferred_plants: f.preferred_plants.filter(
            item =>
              item !== p.displayName &&
              item !== p.cleanEn &&
              item !== p.name_en &&
              item !== p.id
          )
        }
      } else {
        return {
          ...f,
          preferred_plants: [...f.preferred_plants, p.displayName]
        }
      }
    })
  }

  const clearPreferredPlants = () => {
    setForm(f => ({ ...f, preferred_plants: [] }))
  }

  const handleBudgetChange = (e) => {
    const val = Number(e.target.value)
    setForm(f => ({ ...f, budget: val }))
    setBudget(val)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    const payload = {
      ...form,
      budget: Number(form.budget),
      budget_bdt: Number(form.budget),
    }
    storeSavePreferences(payload)
    setBudget(Number(form.budget))
    try {
      const res = await savePreferences(payload)
      if (res?.session_id) setSessionId(res.session_id)
      onNext()
    } catch (err) {
      setError('Could not save preferences to server. Running in demo mode — continuing anyway.')
      setTimeout(() => { onNext() }, 1500)
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-8">
      <div className="rounded-2xl bg-white shadow-sm border border-slate-100 p-6 space-y-6">
        <h2 className="text-xl font-bold text-slate-900">Your Garden Preferences</h2>

        {/* Garden Type */}
        <div className="space-y-2">
          <label className="block text-sm font-semibold text-slate-700">Garden Type</label>
          <select
            value={form.garden_type}
            onChange={e => setForm(f => ({ ...f, garden_type: e.target.value }))}
            className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm text-slate-800 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
          >
            {GARDEN_TYPES.map(t => <option key={t}>{t}</option>)}
          </select>
        </div>

        {/* Purpose */}
        <div className="space-y-2">
          <label className="block text-sm font-semibold text-slate-700">Purpose</label>
          <div className="flex flex-wrap gap-3">
            {PURPOSES.map(p => (
              <label key={p} className={`flex items-center gap-2 cursor-pointer rounded-xl border px-4 py-2.5 text-sm font-medium transition-all ${
                form.purpose === p
                  ? 'border-emerald-500 bg-emerald-50 text-emerald-700'
                  : 'border-slate-200 bg-white text-slate-600 hover:border-emerald-300'
              }`}>
                <input
                  type="radio"
                  name="purpose"
                  value={p}
                  checked={form.purpose === p}
                  onChange={() => setForm(f => ({ ...f, purpose: p }))}
                  className="sr-only"
                />
                {p}
              </label>
            ))}
          </div>
        </div>

        {/* Budget */}
        <div className="space-y-2">
          <label className="block text-sm font-semibold text-slate-700">Budget</label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 text-sm font-semibold">৳</span>
            <input
              type="number"
              value={form.budget}
              min={1000}
              max={500000}
              onChange={handleBudgetChange}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-8 pr-4 text-sm text-slate-800 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
            />
          </div>
          <p className="text-xs text-slate-400">Min ৳1,000 — Max ৳5,00,000</p>
        </div>

        {/* Experience */}
        <div className="space-y-2">
          <label className="block text-sm font-semibold text-slate-700">Experience Level</label>
          <select
            value={form.experience}
            onChange={e => setForm(f => ({ ...f, experience: e.target.value }))}
            className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm text-slate-800 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
          >
            {EXPERIENCE_LEVELS.map(l => <option key={l}>{l}</option>)}
          </select>
        </div>

        {/* Maintenance */}
        <div className="space-y-2">
          <label className="block text-sm font-semibold text-slate-700">Maintenance Availability</label>
          <div className="flex flex-wrap gap-3">
            {MAINTENANCE_OPTIONS.map(m => (
              <label key={m} className={`flex items-center gap-2 cursor-pointer rounded-xl border px-4 py-2.5 text-sm font-medium transition-all ${
                form.maintenance === m
                  ? 'border-emerald-500 bg-emerald-50 text-emerald-700'
                  : 'border-slate-200 bg-white text-slate-600 hover:border-emerald-300'
              }`}>
                <input
                  type="radio"
                  name="maintenance"
                  value={m}
                  checked={form.maintenance === m}
                  onChange={() => setForm(f => ({ ...f, maintenance: m }))}
                  className="sr-only"
                />
                {m}
              </label>
            ))}
          </div>
        </div>

        {/* Style */}
        <div className="space-y-2">
          <label className="block text-sm font-semibold text-slate-700">Garden Style</label>
          <div className="flex flex-wrap gap-2">
            {STYLE_OPTIONS.map(s => (
              <button
                key={s}
                type="button"
                onClick={() => setForm(f => ({ ...f, style: s }))}
                className={`rounded-full border px-4 py-1.5 text-sm font-semibold transition-all ${
                  form.style === s
                    ? 'border-emerald-500 bg-emerald-500 text-white shadow-md shadow-emerald-500/30'
                    : 'border-slate-200 bg-white text-slate-600 hover:border-emerald-300 hover:text-emerald-700'
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        {/* Water Source */}
        <div className="space-y-2">
          <label className="block text-sm font-semibold text-slate-700">Water Source</label>
          <select
            value={form.water_source}
            onChange={e => setForm(f => ({ ...f, water_source: e.target.value }))}
            className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm text-slate-800 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
          >
            {WATER_OPTIONS.map(w => <option key={w}>{w}</option>)}
          </select>
        </div>

        {/* Preferred Plants Section (Dynamic 50+ Plants Selector) */}
        <div className="space-y-3 pt-2 border-t border-slate-100">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div>
              <div className="flex items-center gap-2">
                <Leaf className="h-4 w-4 text-emerald-600" />
                <label className="text-sm font-semibold text-slate-800">
                  Preferred Rooftop Plants
                </label>
                <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-100">
                  {form.preferred_plants.length} selected
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Select your favorite rooftop crops and herbs to prioritize in Step 3 (Garden Design).
              </p>
            </div>

            {form.preferred_plants.length > 0 && (
              <button
                type="button"
                onClick={clearPreferredPlants}
                className="text-xs font-medium text-slate-400 hover:text-red-500 transition self-start sm:self-auto"
              >
                Clear all ({form.preferred_plants.length})
              </button>
            )}
          </div>

          {/* Search Box & Category Filter Pill Bar */}
          <div className="space-y-2.5 bg-slate-50/80 p-3 rounded-xl border border-slate-200/80">
            {/* Search Input */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search plants by English or Bangla name (e.g. Tomato, লাউ, Strawberry, জবা)..."
                value={plantSearch}
                onChange={e => setPlantSearch(e.target.value)}
                className="w-full rounded-lg border border-slate-200 bg-white py-1.5 pl-9 pr-8 text-xs text-slate-800 placeholder:text-slate-400 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500/20"
              />
              {plantSearch && (
                <button
                  type="button"
                  onClick={() => setPlantSearch('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>

            {/* Quick Category Filter Pills */}
            <div className="flex flex-wrap gap-1.5 pt-0.5">
              {[
                { id: 'All Verified (50)', label: 'All Verified (50)' },
                { id: 'Fruits', label: 'Fruits' },
                { id: 'Vegetables', label: 'Vegetables' },
                { id: 'Leafy', label: 'Leafy' },
                { id: 'Flowers', label: 'Flowers' },
                { id: 'Herbs', label: 'Herbs' },
              ].map(cat => (
                <button
                  key={cat.id}
                  type="button"
                  onClick={() => setPlantCategory(cat.id)}
                  className={`rounded-full px-2.5 py-1 text-[11px] font-semibold transition ${
                    plantCategory === cat.id
                      ? 'bg-emerald-600 text-white shadow-xs'
                      : 'bg-white text-slate-600 border border-slate-200/80 hover:bg-slate-100 hover:text-slate-900'
                  }`}
                >
                  {cat.label}
                </button>
              ))}
            </div>
          </div>

          {/* Dynamic Plant Chips Multi-Select */}
          <div className="flex flex-wrap gap-2 max-h-56 overflow-y-auto p-1 pr-2">
            {filteredPlants.map(plant => {
              const selected = isPlantSelected(plant)
              return (
                <button
                  key={plant.id || plant.cleanEn}
                  type="button"
                  onClick={() => togglePlant(plant)}
                  className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold transition-all ${
                    selected
                      ? 'border-emerald-500 bg-emerald-50 text-emerald-800 shadow-xs ring-1 ring-emerald-500/30'
                      : 'border-slate-200 bg-white text-slate-600 hover:border-emerald-300 hover:bg-slate-50'
                  }`}
                >
                  {selected ? (
                    <Check className="h-3 w-3 text-emerald-600 shrink-0" />
                  ) : null}
                  <span>{plant.displayName}</span>
                  {plant.isVerified && (
                    <span className="text-[10px] text-emerald-600 font-bold opacity-80" title="Verified Research Plant">
                      ★
                    </span>
                  )}
                </button>
              )
            })}
            {filteredPlants.length === 0 && (
              <div className="py-4 text-center text-xs text-slate-400 w-full">
                No plants found matching &ldquo;{plantSearch}&rdquo;. Try another search or category.
              </div>
            )}
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-xl bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
          {error}
        </div>
      )}

      <div className="flex justify-end gap-3">
        <button
          type="submit"
          disabled={loading}
          className="flex items-center gap-2 rounded-xl bg-emerald-600 px-6 py-2.5 text-sm font-semibold text-white shadow-md shadow-emerald-600/25 transition-all hover:bg-emerald-700 disabled:opacity-50"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          Save &amp; Continue
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </form>
  )
}
