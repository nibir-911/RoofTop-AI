/**
 * GardenDesign.jsx — Step 3: Generative AI Rooftop Garden Visualizer
 *
 * Real Generative AI Pipeline:
 * - Sends base64 uploaded image + normalized boundary pins + zones to POST /api/generate-design
 * - Dynamic generation loading state with progressive architectural status messages
 * - Displays dynamic generated output directly in the Before/After split slider (pointer capture, no 16:9 crop).
 */
import { useState, useRef, useEffect, useCallback } from 'react'
import { useAppStore } from '../store/useAppStore'
import { getExplanation, generateDesign } from '../services/api'
import {
  PROMPT_VERSION,
  SEND_LONG_SIDE,
  SEND_QUALITY,
  makeFingerprint,
  plantsKeyOf,
} from '../utils/renderConfig'
import { preparePhotoForAI } from '../utils/imagePipeline'
import {
  Sparkles, Eye, Download, ZoomIn, Sun, Moon, Cloud,
  CheckCircle2, ChevronRight, ChevronLeft, AlertTriangle, Loader2,
  ShieldCheck, Info, Camera, RefreshCw, Cpu
} from 'lucide-react'

// ─── Architectural Style definitions ──────────────────────────────────────────
const VARIANTS = [
  {
    id: 'Productive',
    label: 'Productive (Max Yield)',
    tag: 'High Edible Yield',
    desc: 'Dense edible crops — tomatoes, chillies, eggplant, lemon — in Full Sun zones. Walkways kept fully clear for easy harvesting.',
    accent: 'border-emerald-500 bg-emerald-50/60 text-emerald-800',
  },
  {
    id: 'Colorful',
    label: 'Colorful & Aesthetic',
    tag: 'Flowering Oasis',
    desc: 'Vibrant marigolds, roses, and bougainvillea with lush climbing jasmine and cascading ivy draped along the perimeter railings.',
    accent: 'border-amber-500 bg-amber-50/60 text-amber-800',
  },
  {
    id: 'Balanced',
    label: 'Balanced Oasis',
    tag: 'Optimal Balance',
    desc: 'Harmonious mix of dwarf citrus shrubs, culinary herbs, companion flowers, and open stone-paved walking corridors.',
    accent: 'border-teal-500 bg-teal-50/60 text-teal-800',
  },
]

const LIGHTING_OPTS = [
  { id: 'daylight', label: 'Daylight', Icon: Sun   },
  { id: 'evening',  label: 'Evening',  Icon: Moon  },
  { id: 'shadow',   label: 'Overcast', Icon: Cloud },
]

const VIEW_SLOTS = [
  { id: 'view_1', label: 'View 1: North (AB)', edge: 'Side AB' },
  { id: 'view_2', label: 'View 2: East (BC)',  edge: 'Side BC' },
  { id: 'view_3', label: 'View 3: South (CD)', edge: 'Side CD' },
  { id: 'view_4', label: 'View 4: West (DA)',  edge: 'Side DA' },
]

// URL Sanitizer: Aggressively purge any legacy glove or dummy URLs from memory/store
const sanitizePhotoUrl = (url) => {
  if (!url || typeof url !== 'string') return null
  if (
    url.includes('1501004318641') ||
    url.includes('1622383563227') ||
    url.toLowerCase().includes('glove')
  ) {
    return null
  }
  return url
}

const LOADING_MESSAGES = [
  "Analyzing structural grid & perimeter boundary...",
  "Synthesizing 3D cedar planter boxes & stone walkway corridors...",
  "Allocating companion crops to Full Sun and Shade zones...",
  "Applying photorealistic architectural lighting & cascading foliage...",
  "Finalizing high-resolution garden rendering..."
]

// ─── Component ────────────────────────────────────────────────────────────────
export default function GardenDesign({ onNext, onBack }) {
  const {
    sessionId,
    preferences,
    roofDimensions,
    roofPhotos,
    activePhotoIdx,
    setActivePhotoIdx,
    gridCells,
    selectedVariant,
    setSelectedVariant,
    visualizationsByIndex,
    setVisualizationForIndex,
    selectedPlants: storePlants,
  } = useAppStore()

  const [activeSlot, setActiveSlot] = useState(activePhotoIdx || 0)
  const [lighting, setLighting]     = useState('daylight')
  const [sliderX, setSliderX]       = useState(50)
  const [explanations, setExplanations] = useState([])
  const [natRatio, setNatRatio]     = useState(4 / 3)
  
  // Real Generative AI State & Locks
  const [isGenerating, setIsGenerating] = useState(false)
  const [loadingStepIdx, setLoadingStepIdx] = useState(0)
  const [generatedResult, setGeneratedResult] = useState(null)
  const [generationError, setGenerationError] = useState(null)

  const isGeneratingRef = useRef(false)
  const requestIdRef = useRef(0)
  const failedFingerprintRef = useRef(null)

  const sliderRef  = useRef(null)
  const isDragging = useRef(false)

  const activePhoto = roofPhotos?.[activeSlot] || { url: null, base64: null, railingPts: [], markedZones: [], photoId: null }

  const rawPlants = (storePlants && storePlants.length > 0)
    ? storePlants
    : (preferences?.preferred_plants || preferences?.selected_plants || preferences?.selectedPlants || [])

  const currentFingerprint = makeFingerprint({
    photoId: activePhoto?.photoId,
    pins: activePhoto?.railingPts,
    zones: activePhoto?.markedZones,
    variant: selectedVariant,
    lighting,
    plants: rawPlants,
  })

  // Selection logic: newest first
  const activeRender = (generatedResult?.slotIndex === activeSlot && generatedResult?.status === 'ok')
    ? generatedResult
    : visualizationsByIndex?.[activeSlot]

  const isStale = Boolean(activeRender && activeRender.fingerprint !== currentFingerprint)
  const beforeSrc = activeRender?.sourceDataUrl || sanitizePhotoUrl(activePhoto?.url) || activePhoto?.base64
  const afterSrc = activeRender?.status === 'ok' ? activeRender.preview_data_url : null
  const ratio = (activeRender?.width && activeRender?.height)
    ? (activeRender.width / activeRender.height)
    : natRatio

  const uploadedSlotsCount = (roofPhotos || []).filter(p => Boolean(p?.url || p?.base64)).length

  // Step loading text rotation
  useEffect(() => {
    let interval
    if (isGenerating) {
      interval = setInterval(() => {
        setLoadingStepIdx((prev) => (prev + 1) % LOADING_MESSAGES.length)
      }, 1400)
    }
    return () => clearInterval(interval)
  }, [isGenerating])

  // Fetch companion explanations
  useEffect(() => {
    const selectedPlants = preferences?.preferred_plants || []
    getExplanation({ session_id: sessionId || 'default_session', variant: selectedVariant, selected_plants: selectedPlants })
      .then(r => {
        const list = r.data?.explanations
        if (Array.isArray(list) && list.length > 0) setExplanations(list)
      })
      .catch(() => {})
  }, [selectedVariant, sessionId, preferences])

  // ── Core Generative AI Trigger with In-Flight Guard & Deduplication ─────────
  const handleGenerateAI = useCallback(async (force = false) => {
    const isForce = force === true
    if (isForce) {
      failedFingerprintRef.current = null
    }

    // 1. In-flight guard: prevent concurrent duplicate requests from firing
    if (isGeneratingRef.current) {
      console.log('[GardenDesign] AI generation already in progress. Guarding against duplicate concurrent call.')
      return
    }

    const currentPlants = (storePlants && storePlants.length > 0)
      ? storePlants
      : (preferences?.preferred_plants || preferences?.selected_plants || preferences?.selectedPlants || [])
    const selectedPlants = plantsKeyOf(currentPlants)

    const thisFingerprint = makeFingerprint({
      photoId: activePhoto?.photoId,
      pins: activePhoto?.railingPts,
      zones: activePhoto?.markedZones,
      variant: selectedVariant,
      lighting,
      plants: currentPlants,
    })

    // 2. Cached render check
    const cachedSlotRender = visualizationsByIndex?.[activeSlot]
    if (!isForce && cachedSlotRender?.status === 'ok' && cachedSlotRender?.fingerprint === thisFingerprint) {
      console.log(`[GardenDesign] Loading cached render for Angle ${activeSlot + 1}.`)
      setGeneratedResult(cachedSlotRender)
      setGenerationError(null)
      return
    }

    // 3. Prepare photo using single client pipeline
    let prepared = null
    try {
      prepared = await preparePhotoForAI(activePhoto, SEND_LONG_SIDE, SEND_QUALITY)
    } catch (err) {
      console.warn('Failed to prepare photo:', err)
    }

    if (!prepared?.dataUrl) {
      setGenerationError('Upload a photo for this view in Step 2')
      return
    }

    isGeneratingRef.current = true
    setIsGenerating(true)
    setLoadingStepIdx(0)
    setGenerationError(null)

    const thisRequestId = ++requestIdRef.current

    try {
      const boundaryPins = activePhoto?.railingPts || []

      const payload = {
        image_base64: prepared.dataUrl,
        image_width: prepared.width,
        image_height: prepared.height,
        boundary_pins: boundaryPins,
        pins_space: 'normalized',
        zones: activePhoto?.markedZones || [],
        grid_cells: {},
        variant: selectedVariant,
        selected_plants: selectedPlants,
        lighting: lighting,
        view_id: VIEW_SLOTS[activeSlot].id,
        view_index: activeSlot,
        session_id: sessionId,
        regenerate_nonce: isForce ? (crypto?.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2)) : null,
        client_fingerprint: thisFingerprint,
      }

      console.log(`[GardenDesign] Sending payload for angle ${activeSlot + 1}: ${boundaryPins.length} pins, fingerprint: ${thisFingerprint}`)

      const res = await generateDesign(payload)

      // Guard against stale asynchronous responses
      if (thisRequestId !== requestIdRef.current) {
        console.log('[GardenDesign] Dropping stale response for request id:', thisRequestId)
        return
      }

      if (res?.data?.status === 'ok' && res.data.preview_data_url) {
        const safeUrl = sanitizePhotoUrl(res.data.preview_data_url) || res.data.preview_data_url
        const resultData = {
          ...res.data,
          preview_data_url: safeUrl,
          image_url: safeUrl,
          fingerprint: thisFingerprint,
          slotIndex: activeSlot,
          variant: selectedVariant,
          lighting: lighting,
          sourceDataUrl: prepared.dataUrl,
          width: prepared.width,
          height: prepared.height,
        }
        setGeneratedResult(resultData)
        if (setVisualizationForIndex) {
          setVisualizationForIndex(activeSlot, resultData)
        }
        setSliderX(50)
        setGenerationError(null)
        failedFingerprintRef.current = null
      } else {
        throw new Error(res?.data?.detail || res?.data?.message || 'Failed to generate design')
      }
    } catch (err) {
      if (thisRequestId !== requestIdRef.current) return
      console.warn('AI Generation API error:', err)
      const errorMsg = err?.response?.data?.detail || err?.message || 'AI Generation request timed out or unavailable.'
      setGenerationError(errorMsg)
      failedFingerprintRef.current = thisFingerprint
    } finally {
      isGeneratingRef.current = false
      setIsGenerating(false)
    }
  }, [activePhoto, selectedVariant, lighting, sessionId, activeSlot, preferences, visualizationsByIndex, setVisualizationForIndex, storePlants])

  // Trigger generation automatically with 350ms debounce
  useEffect(() => {
    const hasPhoto = Boolean(activePhoto?.url || activePhoto?.base64 || activePhoto?.file)
    if (!hasPhoto) return

    const currentPlants = (storePlants && storePlants.length > 0)
      ? storePlants
      : (preferences?.preferred_plants || preferences?.selected_plants || preferences?.selectedPlants || [])
    const thisFingerprint = makeFingerprint({
      photoId: activePhoto?.photoId,
      pins: activePhoto?.railingPts,
      zones: activePhoto?.markedZones,
      variant: selectedVariant,
      lighting,
      plants: currentPlants,
    })

    const cached = visualizationsByIndex?.[activeSlot]
    if (cached?.status === 'ok' && cached?.fingerprint === thisFingerprint) {
      setGeneratedResult(cached)
      setGenerationError(null)
      return
    }

    if (failedFingerprintRef.current === thisFingerprint) {
      return
    }

    const timer = setTimeout(() => {
      handleGenerateAI(false)
    }, 350)
    return () => clearTimeout(timer)
  }, [selectedVariant, lighting, activeSlot, activePhoto, handleGenerateAI, visualizationsByIndex, storePlants, preferences])

  // ── Slider pointer event logic (setPointerCapture) ──────────────────────
  const updateSlider = (clientX) => {
    if (!sliderRef.current) return
    const rect = sliderRef.current.getBoundingClientRect()
    const pct  = Math.max(0, Math.min(100, ((clientX - rect.left) / rect.width) * 100))
    setSliderX(pct)
  }

  const onPointerDown = (e) => {
    e.currentTarget.setPointerCapture(e.pointerId)
    isDragging.current = true
    updateSlider(e.clientX)
  }

  const onPointerMove = (e) => {
    if (isDragging.current) updateSlider(e.clientX)
  }

  const onPointerUp = (e) => {
    isDragging.current = false
    try {
      e.currentTarget.releasePointerCapture(e.pointerId)
    } catch {}
  }

  // ── Stats from Step 2 grid ──────────────────────────────────────────────
  const cellsList      = gridCells ? Object.values(gridCells) : []
  const gardeningCount = cellsList.filter(c => c.zone === 'GARDENING').length
  const walkwayCount   = cellsList.filter(c => c.zone === 'WALKWAY').length
  const fullSunCount   = cellsList.filter(c => c.sunlight === 'FULL_SUN' && c.zone === 'GARDENING').length
  const shadeCount     = cellsList.filter(c => c.sunlight === 'SHADE'    && c.zone === 'GARDENING').length

  const downloadAfter = () => {
    if (!afterSrc) return
    const a = document.createElement('a')
    a.href = afterSrc
    a.download = `rooftopgreen-${selectedVariant}-${lighting}-design.jpg`
    a.click()
  }

  return (
    <div className="space-y-6">

      {/* ── Header ── */}
      <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-emerald-600" />
              Generative AI Rooftop Garden Visualizer
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Photorealistic architectural generation synthesizing your real rooftop photo with mapped engineering zones.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => handleGenerateAI(true)}
              disabled={isGenerating}
              className="flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2 text-xs font-bold text-white shadow-sm shadow-emerald-600/25 hover:bg-emerald-700 transition disabled:opacity-50"
            >
              {isGenerating ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
              {isGenerating ? 'AI Synthesizing...' : 'Re-Generate AI Preview'}
            </button>
          </div>
        </div>
      </div>

      {/* ── Architectural Style Selector ── */}
      <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-slate-500 text-xs uppercase tracking-wider">
            Select Garden Architectural Style
          </h3>
          <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-100">
            {gardeningCount || 'All'} Planter Zones
          </span>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          {VARIANTS.map(v => (
            <button
              key={v.id}
              type="button"
              onClick={() => setSelectedVariant(v.id)}
              className={`flex flex-col text-left rounded-2xl border p-4 transition-all ${
                selectedVariant === v.id
                  ? `${v.accent} ring-2 ring-emerald-500/20 shadow-md`
                  : 'border-slate-200 bg-white hover:border-emerald-300 hover:shadow-sm'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-bold text-slate-900">{v.label}</span>
                {selectedVariant === v.id && <CheckCircle2 className="h-4 w-4 text-emerald-600" />}
              </div>
              <span className="text-[10px] font-bold text-emerald-700 uppercase tracking-wider mt-1">{v.tag}</span>
              <p className="mt-2 text-xs text-slate-600 leading-relaxed">{v.desc}</p>
            </button>
          ))}
        </div>
      </div>

      {/* ── Multi-Angle Roof Selector & Per-Photo Visualization Tabs ── */}
      <div className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm space-y-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
              <Camera className="h-4 w-4 text-emerald-600" />
              Multi-Angle Rooftop Views ({uploadedSlotsCount} of 4 Uploaded)
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Select any angle below to preview or generate its Before/After AI visualization.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {VIEW_SLOTS.map((slot, idx) => {
            const p = roofPhotos?.[idx]
            const hasPhoto = Boolean(p?.url || p?.base64)
            const isSelected = activeSlot === idx
            const renderData = visualizationsByIndex?.[idx]
            const isRendered = Boolean(renderData?.status === 'ok' && renderData?.preview_data_url)
            const thumbSrc = (isRendered ? renderData.preview_data_url : null) || p?.url || p?.base64 || null

            return (
              <button
                key={slot.id}
                type="button"
                disabled={!hasPhoto}
                onClick={() => {
                  setActiveSlot(idx)
                  setActivePhotoIdx(idx)
                  setGenerationError(null)
                }}
                className={`group relative flex flex-col rounded-xl border-2 p-2.5 text-left transition-all ${
                  isSelected
                    ? 'border-emerald-500 bg-emerald-50/40 ring-2 ring-emerald-500/20 shadow-sm'
                    : hasPhoto
                    ? 'border-slate-200 bg-white hover:border-emerald-300 hover:shadow-sm'
                    : 'border-dashed border-slate-200 bg-slate-50/50 opacity-60 cursor-not-allowed'
                }`}
              >
                {/* Top Label & Status Badge */}
                <div className="flex items-center justify-between mb-1.5 w-full">
                  <span className="text-xs font-bold text-slate-800 truncate">
                    Roof Angle {idx + 1}
                  </span>
                  {hasPhoto ? (
                    isRendered ? (
                      <span className="inline-flex items-center gap-0.5 text-[10px] font-bold text-emerald-700 bg-emerald-100 px-1.5 py-0.5 rounded-full">
                        Rendered ✓
                      </span>
                    ) : (
                      <span className="inline-flex items-center text-[10px] font-semibold text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded-full border border-amber-200/60">
                        Ready to Visualize
                      </span>
                    )
                  ) : (
                    <span className="text-[10px] text-slate-400">Empty</span>
                  )}
                </div>

                {/* Thumbnail Preview */}
                <div className="relative aspect-[16/10] w-full rounded-lg overflow-hidden bg-slate-100 border border-slate-200/60 flex items-center justify-center">
                  {thumbSrc ? (
                    <img src={thumbSrc} alt={`Angle ${idx + 1}`} className="w-full h-full object-cover" />
                  ) : (
                    <Camera className="h-5 w-5 text-slate-300" />
                  )}
                  {isSelected && (
                    <div className="absolute inset-0 bg-emerald-600/10 border-2 border-emerald-500 rounded-lg pointer-events-none" />
                  )}
                </div>

                {/* Edge metadata */}
                <span className="text-[10px] text-slate-500 mt-1.5 truncate">
                  {slot.edge}
                </span>
              </button>
            )
          })}
        </div>

        {/* Informative Note */}
        <div className="rounded-xl bg-emerald-50/60 border border-emerald-200/60 p-2.5 text-[11px] text-emerald-900 flex items-center gap-2">
          <Sparkles className="h-4 w-4 shrink-0 text-emerald-600" />
          <span>
            <strong>Engineering grid &amp; BOM calculate across your total mapped roof area;</strong> switch angles above to preview visualizations for each side.
          </span>
        </div>
      </div>

      {/* ── Lighting Controls ── */}
      <div className="flex items-center justify-between flex-wrap gap-3 rounded-2xl bg-slate-100/80 border border-slate-200 px-4 py-3">
        <span className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
          <Sun className="h-4 w-4 text-amber-500" />
          Active View: {VIEW_SLOTS[activeSlot].label}
        </span>

        {/* Lighting selector */}
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-bold text-slate-600 mr-1">Lighting:</span>
          {LIGHTING_OPTS.map(({ id, label, Icon }) => (
            <button
              key={id}
              type="button"
              onClick={() => setLighting(id)}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-bold transition ${
                lighting === id
                  ? 'bg-slate-900 text-white'
                  : 'bg-white text-slate-600 hover:bg-slate-200'
              }`}
            >
              <Icon className="h-3.5 w-3.5" /> {label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Before / After Split Viewer ── */}
      <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h3 className="font-bold text-slate-900 flex items-center gap-2 text-base">
              <Eye className="h-4 w-4 text-emerald-600" />
              Dynamic AI Garden Render — {VIEW_SLOTS[activeSlot].label}
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Drag the central divider to compare your original photo (Before) with the AI architectural rendering (After).
            </p>
          </div>
          <div className="flex items-center gap-2">
            {activeRender?.engine && (
              <span className="rounded-lg bg-slate-100 border border-slate-200 px-2.5 py-1 text-[11px] font-semibold text-slate-700 flex items-center gap-1.5">
                <Cpu className="h-3 w-3 text-emerald-600" />
                Pipeline: {activeRender.engine} ({activeRender.elapsed_seconds || 0}s)
              </span>
            )}
            <button
              type="button"
              onClick={() => handleGenerateAI(true)}
              disabled={isGenerating}
              className="flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50 transition shadow-sm"
              title="Regenerate garden design for current view"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isGenerating ? 'animate-spin text-emerald-600' : 'text-slate-500'}`} />
              Regenerate
            </button>
            <button
              type="button"
              onClick={downloadAfter}
              disabled={!afterSrc}
              className="flex items-center gap-1.5 rounded-xl bg-emerald-600 px-3.5 py-1.5 text-xs font-bold text-white hover:bg-emerald-700 transition shadow-sm disabled:opacity-50"
            >
              <Download className="h-3.5 w-3.5" /> Download Render
            </button>
          </div>
        </div>

        {/* ── Error / Notice Banner ── */}
        {generationError && (
          <div className="rounded-xl bg-amber-50 border border-amber-200 p-4 text-xs text-amber-900 flex items-start justify-between gap-3">
            <div className="flex items-start gap-2.5">
              <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600 mt-0.5" />
              <div>
                <p className="font-semibold text-amber-900">
                  Remote Generative AI Notice
                </p>
                <p className="text-amber-800 mt-0.5">
                  {generationError}
                </p>
                <p className="text-[11px] text-amber-700 mt-1">
                  {afterSrc ? 'Showing your previous render.' : 'Displaying your original rooftop photo.'}
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => handleGenerateAI(true)}
              disabled={isGenerating}
              className="shrink-0 flex items-center gap-1 px-3 py-1.5 rounded-lg bg-amber-200 hover:bg-amber-300 font-semibold text-amber-900 text-xs transition disabled:opacity-50"
            >
              <RefreshCw className={`h-3 w-3 ${isGenerating ? 'animate-spin' : ''}`} /> Retry
            </button>
          </div>
        )}

        {/* ── Split Slider Canvas Container ── */}
        <div className="mx-auto" style={{ width: `min(100%, calc(75vh * ${ratio}))` }}>
          <div
            ref={sliderRef}
            className="relative overflow-hidden rounded-2xl bg-slate-900 select-none shadow-lg"
            style={{ aspectRatio: String(ratio), touchAction: 'none', cursor: 'col-resize' }}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onPointerCancel={onPointerUp}
          >
            {/* Dynamic AI Loading Overlay */}
            {isGenerating && (
              <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-slate-950/80 backdrop-blur-sm text-center p-6">
                <div className="relative mb-4">
                  <div className="h-16 w-16 rounded-full border-4 border-emerald-500/20 border-t-emerald-500 animate-spin" />
                  <Sparkles className="absolute inset-0 m-auto h-6 w-6 text-emerald-400 animate-pulse" />
                </div>
                <h4 className="text-base font-bold text-white mb-1">Generative AI Engine Active</h4>
                <p className="text-xs text-emerald-400 font-medium transition-all duration-300">
                  {LOADING_MESSAGES[loadingStepIdx]}
                </p>
                <div className="mt-4 flex gap-1.5">
                  {LOADING_MESSAGES.map((_, i) => (
                    <span
                      key={i}
                      className={`h-1.5 rounded-full transition-all duration-300 ${
                        i === loadingStepIdx ? 'w-6 bg-emerald-500' : 'w-1.5 bg-slate-700'
                      }`}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* AFTER: Generated AI Garden Rendering */}
            {afterSrc ? (
              <img
                key={activeRender?.request_id || 'none'}
                src={afterSrc}
                alt="AI render"
                draggable={false}
                decoding="sync"
                className="absolute inset-0 h-full w-full"
                style={{ objectFit: 'fill' }}
              />
            ) : (
              <div className="absolute inset-0 flex items-center justify-center bg-slate-800 text-slate-400 text-xs">
                {isGenerating ? 'Synthesizing...' : 'No render yet. Click Re-Generate AI Preview above'}
              </div>
            )}

            {/* BEFORE: Original rooftop photo (clipped by slider) */}
            {beforeSrc ? (
              <img
                src={beforeSrc}
                alt="Original rooftop photo"
                draggable={false}
                decoding="sync"
                onLoad={(e) => {
                  if (e.currentTarget.naturalWidth && e.currentTarget.naturalHeight) {
                    setNatRatio(e.currentTarget.naturalWidth / e.currentTarget.naturalHeight)
                  }
                }}
                className="absolute inset-0 h-full w-full"
                style={{ objectFit: 'fill', clipPath: `inset(0 ${100 - sliderX}% 0 0)` }}
              />
            ) : (
              <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-800 text-center p-4">
                <Camera className="h-8 w-8 text-slate-500 mb-2" />
                <span className="text-xs text-slate-400">
                  No photo uploaded for {VIEW_SLOTS[activeSlot].label}
                </span>
              </div>
            )}

            {/* Central Divider Handle */}
            {afterSrc && (
              <div
                className="absolute top-0 bottom-0 w-0.5 bg-white shadow-2xl pointer-events-none"
                style={{ left: `${sliderX}%` }}
              >
                <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 bg-white rounded-full p-2 shadow-xl border border-slate-200">
                  <ZoomIn className="h-4 w-4 text-slate-700" />
                </div>
              </div>
            )}

            {/* Badges */}
            <span className="absolute top-3 left-3 rounded-full bg-slate-900/85 px-3 py-1 text-[10px] font-bold text-white backdrop-blur-sm pointer-events-none border border-white/10">
              ◀ BEFORE (YOUR ROOF)
            </span>
            <span className="absolute top-3 right-3 rounded-full bg-emerald-600/90 px-3 py-1 text-[10px] font-bold text-white backdrop-blur-sm pointer-events-none border border-emerald-400/30">
              AFTER (AI ARCHITECTURAL RENDER) ▶
            </span>
            {isStale && (
              <span className="absolute top-12 right-3 rounded-full bg-amber-500/90 px-3 py-1 text-[10px] font-bold text-white backdrop-blur-sm pointer-events-none border border-amber-300/40">
                Outdated — inputs changed
              </span>
            )}
            {afterSrc && (
              <span className="absolute bottom-3 left-1/2 -translate-x-1/2 rounded-full bg-black/60 px-3 py-0.5 text-[10px] font-medium text-white/90 backdrop-blur-sm pointer-events-none">
                ← Drag slider to compare →
              </span>
            )}
          </div>
        </div>

        {/* Disclaimer */}
        <div className="rounded-xl bg-amber-50 border border-amber-200 px-4 py-3 text-xs text-amber-800 flex items-start gap-2">
          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5 text-amber-600" />
          <span>
            {activeRender?.disclaimer ||
              '🌿 Architectural Garden Visualization: Generated from your Step 2 photo markup. Engineering grid layout and wet-load calculations remain the structural source of truth.'}
          </span>
        </div>
      </div>

      {/* ── Engineering Compliance Metrics ── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Planting Cells',  value: gardeningCount || '—', sub: `${selectedVariant} Style`,  color: 'text-emerald-700', bg: 'bg-emerald-50/60 border-emerald-200' },
          { label: 'Clear Walkways', value: walkwayCount    || '—', sub: '100% Unobstructed',         color: 'text-slate-800',   bg: 'bg-slate-50 border-slate-200' },
          { label: 'Full Sun Zones', value: fullSunCount    || '—', sub: 'Fruiting Crops',            color: 'text-yellow-700',  bg: 'bg-yellow-50/60 border-yellow-200' },
          { label: 'Shade Zones',    value: shadeCount      || '—', sub: 'Herbs & Ferns',             color: 'text-purple-700',  bg: 'bg-purple-50/60 border-purple-200' },
        ].map(s => (
          <div key={s.label} className={`rounded-xl border p-3 text-center ${s.bg}`}>
            <div className="text-[11px] font-semibold uppercase text-slate-500">{s.label}</div>
            <div className={`text-2xl font-bold mt-0.5 ${s.color}`}>{s.value}</div>
            <div className="text-[10px] text-slate-400 mt-0.5">{s.sub}</div>
          </div>
        ))}
      </div>

      {/* ── Horticultural Design Principles ── */}
      <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm space-y-4">
        <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-emerald-600" />
          Horticultural Companion Principles &amp; Engineering Rationale
        </h3>

        <div className="rounded-xl bg-emerald-50/70 border border-emerald-100 p-4 space-y-2">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-emerald-800">
            <Info className="h-4 w-4" />
            {selectedVariant} — Agronomic Companion Plan
          </div>
          <ul className="space-y-1.5 text-xs text-emerald-950">
            {(explanations.length > 0 ? explanations : [
              'Sunlight Zone Matching: Edible crops (tomatoes, chillies) placed strictly in Full Sun cells.',
              'Access Corridors: Minimum 60 cm clear walking corridors maintained between planters.',
              'Railing Greenery: Perimeter planters host climbing jasmine and cascading ivy along marked boundary.',
              'Structural Load: Planter beds positioned over load-bearing structural roof columns.'
            ]).map((exp, i) => (
              <li key={i} className="flex items-start gap-1.5">
                <span className="text-emerald-600 font-bold mt-0.5">•</span>
                <span>{exp}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* ── Navigation ── */}
      <div className="flex justify-between items-center pt-2">
        <button
          type="button"
          onClick={onBack}
          className="flex items-center gap-2 rounded-xl border border-slate-200 px-5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition"
        >
          <ChevronLeft className="h-4 w-4" /> Back to Roof Mapping
        </button>
        <button
          type="button"
          onClick={onNext}
          className="flex items-center gap-2 rounded-xl bg-emerald-600 px-6 py-2.5 text-sm font-semibold text-white shadow-md shadow-emerald-600/25 hover:bg-emerald-700 transition"
        >
          View Materials &amp; Growing Guide <ChevronRight className="h-4 w-4" />
        </button>
      </div>

    </div>
  )
}
