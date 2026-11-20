/**
 * RoofCapture.jsx (Step 2: Photo-Based Roof Mapping & Zone Marking)
 * ───────────────────────────────────────────────────────────────────
 * • 100% User-driven rooftop angle photo upload & perspective floor mapping
 * • Upload up to 4 real rooftop photos in a 2x2 grid (North, East, South, West)
 * • Single Coordinate Contract:
 *   - Boundary pins (A, B, C, D) are normalized {x: 0..1, y: 0..1} of the full photo
 *   - Drag & fine-tune boundary pins directly on the photo
 *   - Displays photo at its exact natural aspect ratio without clamping or stretching
 * • Zone Paint Tool: manually assign Full Sun, Shade, Walkway, or Obstacle zones
 * • Under the hood: maps photo markup to structural 2D grid cells (A1, B1, ...)
 */
import { useState, useRef, useCallback, useEffect } from 'react'
import { useAppStore } from '../store/useAppStore'
import {
  saveCellConditions,
} from '../services/api'
import {
  Camera, MapPin, Trash2, CheckCircle2, ChevronRight, ChevronLeft,
  Move, Layers, ShieldAlert, AlertTriangle, RefreshCw
} from 'lucide-react'

const VIEW_SLOTS = [
  { id: 'view_1', label: 'View 1: North Railing (AB)', edge: 'Side AB', desc: 'Front / North boundary' },
  { id: 'view_2', label: 'View 2: East Railing (BC)',  edge: 'Side BC', desc: 'Right / East boundary' },
  { id: 'view_3', label: 'View 3: South Railing (CD)', edge: 'Side CD', desc: 'Back / South boundary' },
  { id: 'view_4', label: 'View 4: West Railing (DA)',  edge: 'Side DA', desc: 'Left / West boundary' },
]

const SAMPLE_PHOTOS = [
  'https://images.unsplash.com/photo-1513836279014-a89f7a76ae86?auto=format&fit=crop&w=960&q=80',
  'https://images.unsplash.com/photo-1598880940371-c756e015fea1?auto=format&fit=crop&w=960&q=80',
  'https://images.unsplash.com/photo-1466692476868-aef1dfb1e735?auto=format&fit=crop&w=960&q=80',
  'https://images.unsplash.com/photo-1585320806297-9794b3e4eeae?auto=format&fit=crop&w=960&q=80',
]

const ZONE_TOOLS = [
  { id: 'WALKWAY',  label: 'Walkway Path',            color: '#94a3b8', bg: 'bg-slate-400',  zone: 'WALKWAY',   sun: 'FULL_SUN' },
  { id: 'BLOCKED',  label: 'Obstacle / Tank',         color: '#ef4444', bg: 'bg-red-500',    zone: 'BLOCKED',   sun: 'SHADE' },
  { id: 'SHADE',    label: 'Shade Garden',            color: '#a855f7', bg: 'bg-purple-500', zone: 'GARDENING', sun: 'SHADE' },
  { id: 'FULL_SUN', label: 'Full Sun Garden',         color: '#22c55e', bg: 'bg-emerald-500', zone: 'GARDENING', sun: 'FULL_SUN' },
  { id: 'ERASER',   label: 'Eraser (Restore Garden)', color: '#64748b', bg: 'bg-slate-300 text-slate-800', zone: 'GARDENING', sun: 'FULL_SUN' },
]

export default function RoofCapture({ onNext, onBack }) {
  const {
    sessionId,
    roofDimensions,
    roofPhotos,
    setRoofPhotos,
    activePhotoIdx,
    setActivePhotoIdx,
    gridCells,
    setGridCells,
    clearVisualizationForIndex,
  } = useAppStore()

  // ── local state ──────────────────────────────────────────────────────────
  const [activeSlot, setActiveSlot] = useState(activePhotoIdx || 0)
  const [markupMode, setMarkupMode] = useState('railing') // 'railing' | 'zone'
  const [selectedZoneTool, setSelectedZoneTool] = useState('WALKWAY')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Canvas natural aspect ratio dimensions (NO clamp to 480-720)
  const [canvasDimensions, setCanvasDimensions] = useState({
    width: 960,
    height: 640,
    aspectRatio: '960 / 640',
    naturalAspect: 960 / 640,
  })

  // Pin dragging state
  const draggingPinRef = useRef(null)
  const didDragRef = useRef(false)
  const [isDraggingPin, setIsDraggingPin] = useState(false)
  const [hoveredPinIdx, setHoveredPinIdx] = useState(null)

  // Drag-to-paint state
  const isPaintingRef = useRef(false)
  const lastPaintedCellRef = useRef(null)

  const width = roofDimensions?.width_ft || 20
  const depth = roofDimensions?.depth_ft || 15
  const gridFt = roofDimensions?.grid_ft || 2
  const bearing = roofDimensions?.bearing || 180

  const canvasRef = useRef(null)
  const bgImgRef = useRef(null)
  const fileInput0 = useRef(null)
  const fileInput1 = useRef(null)
  const fileInput2 = useRef(null)
  const fileInput3 = useRef(null)
  const fileInputRefs = [fileInput0, fileInput1, fileInput2, fileInput3]

  const currentSlotData = roofPhotos?.[activeSlot] || { file: null, url: null, base64: null, name: '', photoId: null, railingPts: [], markedZones: [] }
  const railingPts = currentSlotData.railingPts || []

  // Normalized to pixel conversion helper
  const toPx = useCallback((p) => {
    const cw = canvasDimensions.width || 960
    const ch = canvasDimensions.height || 640
    // If already in pixel space (> 1.0), use directly, else scale from 0..1
    const px = p.x <= 1.0 ? p.x * cw : p.x
    const py = p.y <= 1.0 ? p.y * ch : p.y
    return { x: px, y: py }
  }, [canvasDimensions])

  // Helper for excel-style column letter
  function chrCode(c) {
    return c < 26 ? String.fromCharCode(65 + c) : `A${String.fromCharCode(65 + (c % 26))}`
  }

  // ── Helper to generate full default planting zone array (subtractive workflow) ──
  const getDefaultPlantingZones = useCallback(() => {
    const cols = Math.ceil(width / gridFt)
    const rows = Math.ceil(depth / gridFt)
    const defaultZones = []
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const colLetter = chrCode(c)
        const cellId = `${colLetter}${r + 1}`
        defaultZones.push({ cellId, zone: 'GARDENING', sun: 'FULL_SUN', label: 'Full Sun Garden' })
      }
    }
    return defaultZones
  }, [width, depth, gridFt])

  // ── map photo coordinates to structural 2D grid ──────────────────────────
  const syncPhotoToStructuralGrid = useCallback((customPts, customZones) => {
    const cols = Math.ceil(width / gridFt)
    const rows = Math.ceil(depth / gridFt)
    const cells = {}

    const activeZones = customZones || currentSlotData.markedZones || []

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const colLetter = chrCode(c)
        const cellId = `${colLetter}${r + 1}`
        const x0 = c * gridFt
        const y0 = r * gridFt
        const x1 = Math.min((c + 1) * gridFt, width)
        const y1 = Math.min((r + 1) * gridFt, depth)
        const area = (x1 - x0) * (y1 - y0)

        // 100% User-Driven: Default is UNASSIGNED (no auto-placement or auto-coloring)
        let sunlight = 'UNASSIGNED'
        let zone = 'UNASSIGNED'

        const matched = activeZones.find(z => z.cellId === cellId)
        if (matched) {
          zone = matched.zone
          sunlight = matched.sun
        }

        cells[cellId] = {
          id: cellId,
          row: r,
          col: c,
          x0, y0, x1, y1,
          area_sqft: area,
          clipped_area_sqft: area,
          sunlight,
          zone,
        }
      }
    }

    setGridCells(cells)
    return cells
  }, [width, depth, gridFt, currentSlotData.markedZones, setGridCells])

  // Initial grid mount check: if no slot has a url, ensure clean empty grid
  useEffect(() => {
    const hasAnyUrl = Array.isArray(roofPhotos) && roofPhotos.some(p => Boolean(p?.url || p?.base64))
    if (!hasAnyUrl) {
      syncPhotoToStructuralGrid([], [])
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Activate a slot cleanly & sync its specific pins and zones to the structural grid
  const activateSlot = useCallback((idx) => {
    setActiveSlot(idx)
    setActivePhotoIdx(idx)
    const slot = roofPhotos?.[idx]
    syncPhotoToStructuralGrid(slot?.railingPts || [], slot?.markedZones || [])
  }, [roofPhotos, setActivePhotoIdx, syncPhotoToStructuralGrid])

  // ── photo upload handling ────────────────────────────────────────────────
  const handleSlotFileChange = (index, file) => {
    if (!file) return
    if (!file.type.startsWith('image/')) {
      setError('Please upload an image file (JPEG, PNG, WEBP).')
      return
    }
    if (file.size > 20 * 1024 * 1024) {
      setError('Image file too large — max 20 MB.')
      return
    }

    // Revoke previous blob url if any
    const prev = roofPhotos?.[index]
    if (prev?.url && prev.url.startsWith('blob:')) {
      try { URL.revokeObjectURL(prev.url) } catch {}
    }
    clearVisualizationForIndex(index)

    const photoId = `${file.name}|${file.size}|${file.lastModified}|${Date.now()}`
    const reader = new FileReader()
    reader.onload = (ev) => {
      const base64Data = ev.target?.result
      const url = URL.createObjectURL(file)
      const nextPhotos = [...roofPhotos]
      nextPhotos[index] = {
        ...nextPhotos[index],
        file,
        url,
        base64: base64Data,
        name: file.name,
        photoId,
        railingPts: [],
        markedZones: [],
      }
      setRoofPhotos(nextPhotos)
      activateSlot(index)
      setMarkupMode('railing')
      setError(null)
    }
    reader.readAsDataURL(file)
  }

  const handleSlotDrop = (index, e) => {
    e.preventDefault()
    const file = e.dataTransfer.files?.[0]
    if (file) handleSlotFileChange(index, file)
  }

  const loadDemoPhotos = async () => {
    try {
      const demo = await Promise.all(SAMPLE_PHOTOS.map(async (url, i) => {
        let base64 = null
        try {
          const r = await fetch(url, { mode: 'cors' })
          if (r.ok) {
            const b = await r.blob()
            base64 = await new Promise((res) => {
              const reader = new FileReader()
              reader.onload = (e) => res(e.target?.result)
              reader.onerror = () => res(null)
              reader.readAsDataURL(b)
            })
          }
        } catch (e) {
          console.warn('Failed to fetch demo photo blob:', e)
        }
        return {
          file: null,
          url,
          base64,
          name: `Rooftop_Angle_${i + 1}.jpg`,
          photoId: `demo_${i + 1}_${Date.now()}`,
          railingPts: [],
          markedZones: [],
        }
      }))
      setRoofPhotos(demo)
      activateSlot(0)
      setMarkupMode('railing')
      setError(null)
    } catch (err) {
      console.warn('Demo photos load note:', err)
    }
  }

  const removeSlotPhoto = (index) => {
    const prev = roofPhotos?.[index]
    if (prev?.url && prev.url.startsWith('blob:')) {
      try { URL.revokeObjectURL(prev.url) } catch {}
    }
    clearVisualizationForIndex(index)

    const nextPhotos = [...roofPhotos]
    nextPhotos[index] = { file: null, url: null, base64: null, name: '', photoId: null, railingPts: [], markedZones: [] }
    setRoofPhotos(nextPhotos)
    if (activeSlot === index) {
      bgImgRef.current = null
      syncPhotoToStructuralGrid([], [])
      redrawCanvas()
    }
  }

  // ── redraw canvas ────────────────────────────────────────────────────────
  const redrawCanvas = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    // 1. Draw uploaded rooftop photo
    if (bgImgRef.current) {
      ctx.drawImage(bgImgRef.current, 0, 0, canvas.width, canvas.height)
    } else {
      ctx.fillStyle = '#f8fafc'
      ctx.fillRect(0, 0, canvas.width, canvas.height)
      ctx.fillStyle = '#94a3b8'
      ctx.font = 'bold 15px sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText(
        currentSlotData?.url ? 'Loading rooftop photo...' : `Upload photo for ${VIEW_SLOTS[activeSlot].label} to begin mapping`,
        canvas.width / 2,
        canvas.height / 2
      )
    }

    // 2. Draw Railing Boundary Outline (Pins A, B, C, D)
    const pts = (currentSlotData?.railingPts || []).map(toPx)
    if (pts.length > 0) {
      ctx.beginPath()
      ctx.moveTo(pts[0].x, pts[0].y)
      pts.forEach(p => ctx.lineTo(p.x, p.y))
      if (pts.length > 2) ctx.closePath()
      ctx.strokeStyle = 'rgba(250, 204, 21, 0.95)'
      ctx.lineWidth = 3
      ctx.setLineDash([6, 3])
      ctx.stroke()
      ctx.setLineDash([])

      if (pts.length > 2) {
        ctx.fillStyle = 'rgba(250, 204, 21, 0.08)'
        ctx.fill()
      }

      // Draw alphabetical corner pins with drag affordance
      pts.forEach((p, i) => {
        const isHovered = hoveredPinIdx === i
        const isDragged = isDraggingPin && draggingPinRef.current === i
        const radius = isDragged ? 12 : (isHovered ? 11 : 9)

        if (isHovered || isDragged) {
          ctx.beginPath()
          ctx.arc(p.x, p.y, radius + 5, 0, Math.PI * 2)
          ctx.fillStyle = 'rgba(250, 204, 21, 0.35)'
          ctx.fill()
        }

        ctx.beginPath()
        ctx.arc(p.x, p.y, radius, 0, Math.PI * 2)
        ctx.fillStyle = isDragged ? '#f59e0b' : '#facc15'
        ctx.fill()
        ctx.strokeStyle = '#0f172a'
        ctx.lineWidth = 2
        ctx.stroke()
        ctx.fillStyle = '#0f172a'
        ctx.font = 'bold 11px sans-serif'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        ctx.fillText(String.fromCharCode(65 + i), p.x, p.y)
      })
    }

    // Guide overlay when in railing mode and < 4 pins placed
    if (bgImgRef.current && markupMode === 'railing' && pts.length < 4) {
      ctx.save()
      ctx.fillStyle = 'rgba(15, 23, 42, 0.70)'
      const msg = pts.length === 0
        ? 'Click 4 corners on the floor to place Pins A, B, C, D'
        : `Click to place Pin ${String.fromCharCode(65 + pts.length)} (${pts.length}/4 placed)`
      ctx.font = 'bold 13px sans-serif'
      const textW = ctx.measureText(msg).width
      const boxW = textW + 36
      const boxH = 34
      const boxX = (canvas.width - boxW) / 2
      const boxY = 16
      ctx.beginPath()
      ctx.roundRect(boxX, boxY, boxW, boxH, 8)
      ctx.fill()
      ctx.fillStyle = '#ffffff'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(msg, canvas.width / 2, boxY + boxH / 2)
      ctx.restore()
    }

    // 3. Draw Mapped Engineering Grid Overlay on top of Photo (ONLY in 'zone' mode)
    if (markupMode === 'zone' && pts.length >= 3 && gridCells) {
      const minX = Math.min(...pts.map(p => p.x))
      const maxX = Math.max(...pts.map(p => p.x))
      const minY = Math.min(...pts.map(p => p.y))
      const maxY = Math.max(...pts.map(p => p.y))
      const spanX = Math.max(maxX - minX, 10)
      const spanY = Math.max(maxY - minY, 10)

      const cols = Math.ceil(width / gridFt)
      const rows = Math.ceil(depth / gridFt)

      Object.values(gridCells).forEach((cell) => {
        const u0 = cell.col / cols
        const v0 = cell.row / rows
        const u1 = (cell.col + 1) / cols
        const v1 = (cell.row + 1) / rows

        const cx0 = minX + u0 * spanX
        const cy0 = minY + v0 * spanY
        const cw = (u1 - u0) * spanX
        const ch = (v1 - v0) * spanY

        // Cell boundary
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.35)'
        ctx.lineWidth = 1
        ctx.strokeRect(cx0, cy0, cw, ch)

        // Zone badge color
        if (cell.zone === 'WALKWAY') {
          ctx.fillStyle = 'rgba(148, 163, 184, 0.50)'
          ctx.fillRect(cx0, cy0, cw, ch)
          ctx.strokeStyle = 'rgba(148, 163, 184, 0.90)'
          ctx.lineWidth = 1.5
          ctx.strokeRect(cx0 + 1, cy0 + 1, cw - 2, ch - 2)
        } else if (cell.zone === 'BLOCKED') {
          ctx.fillStyle = 'rgba(239, 68, 68, 0.45)'
          ctx.fillRect(cx0, cy0, cw, ch)
          ctx.strokeStyle = 'rgba(239, 68, 68, 0.85)'
          ctx.lineWidth = 1.5
          ctx.strokeRect(cx0 + 1, cy0 + 1, cw - 2, ch - 2)
        } else if (cell.zone === 'GARDENING') {
          if (cell.sunlight === 'SHADE') {
            ctx.fillStyle = 'rgba(168, 85, 247, 0.38)'
            ctx.fillRect(cx0, cy0, cw, ch)
            ctx.strokeStyle = 'rgba(168, 85, 247, 0.70)'
            ctx.lineWidth = 1
            ctx.strokeRect(cx0, cy0, cw, ch)
          } else {
            // Subtle low-opacity green so the rooftop floor remains clearly visible
            ctx.fillStyle = 'rgba(34, 197, 94, 0.16)'
            ctx.fillRect(cx0, cy0, cw, ch)
            ctx.strokeStyle = 'rgba(34, 197, 94, 0.35)'
            ctx.lineWidth = 1
            ctx.strokeRect(cx0, cy0, cw, ch)
          }
        }

        // Cell ID tag
        if (cell.zone && cell.zone !== 'UNASSIGNED') {
          ctx.fillStyle = 'rgba(255, 255, 255, 0.95)'
          ctx.font = 'bold 9px sans-serif'
          ctx.textAlign = 'left'
          ctx.fillText(cell.id, cx0 + 3, cy0 + 11)
        } else {
          ctx.fillStyle = 'rgba(255, 255, 255, 0.40)'
          ctx.font = '8px sans-serif'
          ctx.textAlign = 'left'
          ctx.fillText(cell.id, cx0 + 3, cy0 + 10)
        }
      })
    }
  }, [currentSlotData, activeSlot, gridCells, width, depth, gridFt, hoveredPinIdx, isDraggingPin, markupMode, toPx])

  // Load active photo into background & configure natural aspect ratio (NO clamp)
  useEffect(() => {
    const url = currentSlotData?.url
    if (!url) {
      bgImgRef.current = null
      redrawCanvas()
      return
    }
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => {
      bgImgRef.current = img
      if (img.naturalWidth && img.naturalHeight) {
        const naturalAspect = img.naturalWidth / img.naturalHeight
        const w = 960
        const h = Math.round(w / naturalAspect)
        setCanvasDimensions({
          width: w,
          height: h,
          aspectRatio: `${img.naturalWidth} / ${img.naturalHeight}`,
          naturalAspect,
        })
      }
      redrawCanvas()
    }
    img.src = url
  }, [currentSlotData?.url, redrawCanvas])

  useEffect(() => {
    redrawCanvas()
  }, [redrawCanvas, canvasDimensions])

  // Helper: map client mouse event to canvas coordinate space + normalized coordinates
  const getCanvasCoords = (e) => {
    const canvas = canvasRef.current
    if (!canvas) return { x: 0, y: 0, nx: 0, ny: 0 }
    const rect = canvas.getBoundingClientRect()
    const scaleX = canvas.width / rect.width
    const scaleY = canvas.height / rect.height
    const x = (e.clientX - rect.left) * scaleX
    const y = (e.clientY - rect.top)  * scaleY
    const nx = Math.round(Math.max(0, Math.min(1, x / canvas.width)) * 10000) / 10000
    const ny = Math.round(Math.max(0, Math.min(1, y / canvas.height)) * 10000) / 10000
    return { x, y, nx, ny }
  }

  // ── drag-to-paint & mouse event handlers ──────────────────────────────────
  const paintCellAt = useCallback((x, y) => {
    const pts = (currentSlotData.railingPts || []).map(toPx)
    if (pts.length < 3) return

    const minX = Math.min(...pts.map(p => p.x))
    const maxX = Math.max(...pts.map(p => p.x))
    const minY = Math.min(...pts.map(p => p.y))
    const maxY = Math.max(...pts.map(p => p.y))
    const spanX = Math.max(maxX - minX, 10)
    const spanY = Math.max(maxY - minY, 10)

    if (x < minX || x > maxX || y < minY || y > maxY) return

    const cols = Math.ceil(width / gridFt)
    const rows = Math.ceil(depth / gridFt)

    const col = Math.min(Math.max(Math.floor(((x - minX) / spanX) * cols), 0), cols - 1)
    const row = Math.min(Math.max(Math.floor(((y - minY) / spanY) * rows), 0), rows - 1)

    const colLetter = chrCode(col)
    const cellId = `${colLetter}${row + 1}`

    if (lastPaintedCellRef.current === cellId) return
    lastPaintedCellRef.current = cellId

    const currentZones = currentSlotData.markedZones || []
    let nextZones
    if (selectedZoneTool === 'ERASER') {
      nextZones = currentZones.filter(z => z.cellId !== cellId)
      nextZones.push({ cellId, zone: 'GARDENING', sun: 'FULL_SUN', label: 'Full Sun Garden' })
    } else {
      const tool = ZONE_TOOLS.find(t => t.id === selectedZoneTool) || ZONE_TOOLS[0]
      nextZones = currentZones.filter(z => z.cellId !== cellId)
      nextZones.push({ cellId, zone: tool.zone, sun: tool.sun, label: tool.label })
    }

    const currentPhotos = useAppStore.getState().roofPhotos || []
    const nextPhotos = [...currentPhotos]
    if (nextPhotos[activeSlot]) {
      nextPhotos[activeSlot] = { ...nextPhotos[activeSlot], markedZones: nextZones }
      setRoofPhotos(nextPhotos)
    }
    syncPhotoToStructuralGrid(currentSlotData.railingPts, nextZones)
  }, [currentSlotData.railingPts, currentSlotData.markedZones, activeSlot, width, depth, gridFt, selectedZoneTool, setRoofPhotos, syncPhotoToStructuralGrid, toPx])

  const handleCanvasMouseDown = (e) => {
    // Ignore clicks until image is decoded
    if (!currentSlotData?.url || !bgImgRef.current) return
    const { x, y } = getCanvasCoords(e)
    didDragRef.current = false

    if (markupMode === 'railing') {
      const pts = (currentSlotData.railingPts || []).map(toPx)
      const foundIdx = pts.findIndex(p => Math.hypot(p.x - x, p.y - y) <= 22)
      if (foundIdx !== -1) {
        draggingPinRef.current = foundIdx
        setIsDraggingPin(true)
        return
      }
    } else if (markupMode === 'zone') {
      const pts = (currentSlotData.railingPts || []).map(toPx)
      if (pts.length < 3) {
        setError('Please place 4 boundary pins (A, B, C, D) on the floor first.')
        return
      }
      isPaintingRef.current = true
      lastPaintedCellRef.current = null
      paintCellAt(x, y)
    }
  }

  const handleCanvasMouseMove = (e) => {
    if (!currentSlotData?.url || !bgImgRef.current) return
    const { x, y, nx, ny } = getCanvasCoords(e)
    const pts = (currentSlotData.railingPts || []).map(toPx)

    // Dragging an existing pin
    if (draggingPinRef.current !== null) {
      didDragRef.current = true
      const pinIdx = draggingPinRef.current
      const cWidth = canvasDimensions.width || 960
      const cHeight = canvasDimensions.height || 640
      const marginX = 10 / cWidth
      const marginY = 10 / cHeight
      const clampedNx = Math.round(Math.max(marginX, Math.min(1 - marginX, nx)) * 10000) / 10000
      const clampedNy = Math.round(Math.max(marginY, Math.min(1 - marginY, ny)) * 10000) / 10000

      const updatedRawPts = [...(currentSlotData.railingPts || [])]
      updatedRawPts[pinIdx] = { x: clampedNx, y: clampedNy }

      const nextPhotos = [...roofPhotos]
      nextPhotos[activeSlot] = { ...nextPhotos[activeSlot], railingPts: updatedRawPts }
      setRoofPhotos(nextPhotos)
      syncPhotoToStructuralGrid(updatedRawPts)
      return
    }

    if (markupMode === 'railing') {
      const foundIdx = pts.findIndex(p => Math.hypot(p.x - x, p.y - y) <= 22)
      setHoveredPinIdx(foundIdx !== -1 ? foundIdx : null)
    } else if (markupMode === 'zone') {
      setHoveredPinIdx(null)
      if (isPaintingRef.current) {
        paintCellAt(x, y)
      }
    }
  }

  const handleCanvasMouseUp = (e) => {
    if (draggingPinRef.current !== null) {
      draggingPinRef.current = null
      setIsDraggingPin(false)
      didDragRef.current = false
      return
    }

    if (isPaintingRef.current) {
      isPaintingRef.current = false
      lastPaintedCellRef.current = null
      return
    }

    if (!currentSlotData?.url || !bgImgRef.current) return

    // Regular click in railing mode: add pin up to 4 pins (A, B, C, D)
    if (markupMode === 'railing' && !didDragRef.current) {
      const { nx, ny } = getCanvasCoords(e)
      const rawPts = currentSlotData.railingPts || []
      if (rawPts.length < 4) {
        const nextPts = [...rawPts, { x: nx, y: ny }]
        let nextZones = currentSlotData.markedZones || []

        // Auto-Fill Planting Zone on Pin 4 if currently empty (Smart Subtractive Workflow)
        if (nextPts.length === 4 && (!nextZones || nextZones.length === 0)) {
          nextZones = getDefaultPlantingZones()
          setSelectedZoneTool('WALKWAY')
          setMarkupMode('zone')
        }

        const nextPhotos = [...roofPhotos]
        nextPhotos[activeSlot] = {
          ...nextPhotos[activeSlot],
          railingPts: nextPts,
          markedZones: nextZones,
        }
        setRoofPhotos(nextPhotos)
        syncPhotoToStructuralGrid(nextPts, nextZones)
        if (nextPts.length === 4) {
          setError(null)
        }
      }
    }
  }

  const undoLastPin = () => {
    const rawPts = currentSlotData.railingPts || []
    const nextPts = rawPts.slice(0, -1)
    const nextPhotos = [...roofPhotos]
    nextPhotos[activeSlot] = { ...nextPhotos[activeSlot], railingPts: nextPts }
    setRoofPhotos(nextPhotos)
    syncPhotoToStructuralGrid(nextPts)
  }

  const resetPins = () => {
    const nextPhotos = [...roofPhotos]
    nextPhotos[activeSlot] = { ...nextPhotos[activeSlot], railingPts: [], markedZones: [] }
    setRoofPhotos(nextPhotos)
    syncPhotoToStructuralGrid([])
  }

  const resetAllToPlanting = () => {
    const defaultZones = getDefaultPlantingZones()
    const nextPhotos = [...roofPhotos]
    nextPhotos[activeSlot] = { ...nextPhotos[activeSlot], markedZones: defaultZones }
    setRoofPhotos(nextPhotos)
    syncPhotoToStructuralGrid(currentSlotData.railingPts, defaultZones)
    setSelectedZoneTool('WALKWAY')
  }

  // ── save & proceed to Step 3 ─────────────────────────────────────────────
  const handleSaveAndProceed = async () => {
    setLoading(true)
    try {
      if (gridCells && sessionId) {
        await saveCellConditions({ session_id: sessionId, cells: gridCells }).catch(() => {})
      }
    } catch {
      // demo fallback
    } finally {
      setLoading(false)
      onNext()
    }
  }

  const cellsList = gridCells ? Object.values(gridCells) : []
  const gardeningCount = cellsList.filter(c => c.zone === 'GARDENING').length
  const walkwayCount   = cellsList.filter(c => c.zone === 'WALKWAY').length
  const obstacleCount  = cellsList.filter(c => c.zone === 'BLOCKED').length
  const uploadedCount  = (roofPhotos || []).filter(s => Boolean(s?.url || s?.base64)).length
  const hasAnyPhoto    = uploadedCount > 0
  const hasActivePhoto = Boolean(currentSlotData?.url || currentSlotData?.base64)
  const aspect = canvasDimensions.naturalAspect || (canvasDimensions.width / canvasDimensions.height)

  const uploadedIndices = (roofPhotos || [])
    .map((p, idx) => (Boolean(p?.url || p?.base64) ? idx : null))
    .filter(idx => idx !== null)

  const markedCount = (roofPhotos || []).filter(
    s => Boolean(s?.url || s?.base64) && (s?.railingPts?.length || 0) >= 3
  ).length

  // Find next unmarked uploaded slot after activeSlot first
  let nextTargetSlot = uploadedIndices.find(
    idx => idx > activeSlot && (roofPhotos[idx]?.railingPts?.length || 0) < 3
  )
  // If none after activeSlot, check if any earlier slot is unmarked
  if (nextTargetSlot === undefined) {
    nextTargetSlot = uploadedIndices.find(
      idx => idx !== activeSlot && (roofPhotos[idx]?.railingPts?.length || 0) < 3
    )
  }
  // If all are marked, check if there is another uploaded view after activeSlot
  if (nextTargetSlot === undefined) {
    nextTargetSlot = uploadedIndices.find(idx => idx > activeSlot)
  }

  const hasNextView = nextTargetSlot !== undefined

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <Camera className="h-5 w-5 text-emerald-600" />
              Photo-Based Rooftop Mapping &amp; Garden Planning
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Upload rooftop photos, outline the floor perimeter with 4 boundary pins (A, B, C, D), and paint Sun, Shade, Walkways, and Obstacle zones.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-700 border border-emerald-200">
              {uploadedCount} of 4 Views Uploaded
            </span>
            {import.meta.env.DEV && (
              <button
                type="button"
                onClick={loadDemoPhotos}
                className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700 hover:bg-emerald-50 hover:text-emerald-700 transition"
              >
                ✨ Fill 4 Sample Views
              </button>
            )}
          </div>
        </div>
      </div>

      {/* 2x2 Photo Upload Grid */}
      <div className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
              <Layers className="h-4 w-4 text-emerald-600" />
              Step 2A: Upload Rooftop Angles (2&times;2 Grid)
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Click any photo to make it active for perspective boundary mapping &amp; zone markup below.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {VIEW_SLOTS.map((slotMeta, idx) => {
            const slot = roofPhotos?.[idx]
            const isActive = activeSlot === idx
            const hasImage = Boolean(slot?.url || slot?.base64)
            const ptsCount = slot?.railingPts?.length || 0

            return (
              <div
                key={slotMeta.id}
                onClick={() => {
                  if (!hasImage) fileInputRefs[idx].current?.click()
                  else activateSlot(idx)
                }}
                onDrop={(e) => handleSlotDrop(idx, e)}
                onDragOver={(e) => e.preventDefault()}
                className={`group relative flex flex-col rounded-2xl border-2 transition-all p-3 cursor-pointer ${
                  isActive
                    ? 'border-emerald-500 bg-emerald-50/50 ring-2 ring-emerald-500/20 shadow-md'
                    : hasImage
                    ? 'border-slate-200 bg-white hover:border-emerald-300'
                    : 'border-dashed border-slate-300 bg-slate-50 hover:border-emerald-400'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold ${
                      isActive ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-700'
                    }`}>
                      {idx + 1}
                    </span>
                    <span className="text-xs font-bold text-slate-800">{slotMeta.label}</span>
                  </div>
                  {hasImage ? (
                    ptsCount >= 3 ? (
                      <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200">
                        <CheckCircle2 className="h-3 w-3 text-emerald-600" />
                        ✓ Marked
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-200">
                        <AlertTriangle className="h-3 w-3 text-amber-600" />
                        Needs Pins
                      </span>
                    )
                  ) : (
                    <span className="text-[10px] font-medium text-slate-400">Empty</span>
                  )}
                </div>

                <div className="relative rounded-xl overflow-hidden bg-slate-100 aspect-[16/10] flex items-center justify-center border border-slate-200/60">
                  {hasImage ? (
                    <>
                      <img src={slot.url || slot.base64} alt={slotMeta.label} className="w-full h-full object-cover" />
                      {isActive && (
                        <div className="absolute top-2 left-2 bg-emerald-600 text-white text-[10px] font-bold px-2.5 py-0.5 rounded-full shadow-md flex items-center gap-1">
                          <CheckCircle2 className="h-3 w-3" /> Active on Canvas
                        </div>
                      )}
                      {ptsCount >= 3 ? (
                        <div className="absolute bottom-2 left-2 bg-slate-900/85 text-emerald-300 text-[10px] font-bold px-2 py-0.5 rounded-full backdrop-blur-xs flex items-center gap-1 border border-emerald-500/30">
                          <CheckCircle2 className="h-3 w-3 text-emerald-400" /> ✓ {ptsCount} boundary pins
                        </div>
                      ) : (
                        <div className="absolute bottom-2 left-2 bg-slate-900/85 text-amber-300 text-[10px] font-bold px-2 py-0.5 rounded-full backdrop-blur-xs flex items-center gap-1 border border-amber-500/30">
                          <AlertTriangle className="h-3 w-3 text-amber-400" /> Needs Pins ({ptsCount}/4)
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="flex flex-col items-center justify-center p-4 text-center">
                      <Camera className="h-7 w-7 text-emerald-500/70 mb-1.5" />
                      <span className="text-xs font-bold text-slate-700">Click or Drop Photo Here</span>
                      <span className="text-[10px] text-slate-400 mt-0.5">{slotMeta.desc}</span>
                    </div>
                  )}
                </div>

                <div className="flex items-center justify-between mt-2.5 pt-2 border-t border-slate-100 text-[11px]">
                  <span className="text-slate-500 font-medium truncate max-w-[140px]">
                    {hasImage ? (slot.name || `View ${idx + 1}`) : 'JPEG / PNG / WEBP'}
                  </span>
                  <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                    {hasImage ? (
                      <>
                        <button
                          type="button"
                          onClick={() => activateSlot(idx)}
                          className="font-bold text-emerald-700 underline underline-offset-2"
                        >
                          {isActive ? '● Editing' : 'Select'}
                        </button>
                        <span className="text-slate-300">|</span>
                        <button
                          type="button"
                          onClick={() => fileInputRefs[idx].current?.click()}
                          className="text-slate-500 hover:text-slate-800"
                        >
                          Replace
                        </button>
                        <span className="text-slate-300">|</span>
                        <button
                          type="button"
                          onClick={() => removeSlotPhoto(idx)}
                          className="text-slate-400 hover:text-red-500"
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      </>
                    ) : (
                      <button
                        type="button"
                        onClick={() => fileInputRefs[idx].current?.click()}
                        className="text-emerald-700 font-semibold"
                      >
                        + Select Photo
                      </button>
                    )}
                  </div>
                </div>

                <input
                  ref={fileInputRefs[idx]}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={(e) => handleSlotFileChange(idx, e.target.files?.[0])}
                />
              </div>
            )
          })}
        </div>
      </div>

      {/* Step 2B: Interactive Photo Markup Canvas */}
      <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-3 border-b border-slate-100 pb-4">
          <div>
            <h3 className="font-bold text-slate-900 flex items-center gap-2">
              <MapPin className="h-4 w-4 text-emerald-600" />
              Step 2B: Photo Markup Canvas ({VIEW_SLOTS[activeSlot].label})
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              {markupMode === 'railing'
                ? (railingPts.length < 4
                    ? `Click directly on the photo to place Pin ${String.fromCharCode(65 + railingPts.length)} (${railingPts.length} of 4 placed).`
                    : 'All 4 corner pins placed! Floor mapped to Planting (Full Sun). Drag pins to adjust, or paint walkways and obstacles below.')
                : 'All cells default to Planting (Full Sun). Select Walkway or Obstacle to paint exceptions directly on the grid.'}
            </p>
          </div>

          {/* Mode Switcher */}
          <div className="flex items-center gap-2 bg-slate-100 p-1 rounded-xl">
            <button
              type="button"
              onClick={() => setMarkupMode('railing')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                markupMode === 'railing'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Move className="h-3.5 w-3.5 text-amber-500" />
              1. Floor Boundary &amp; Pins ({railingPts.length}/4)
            </button>
            <button
              type="button"
              onClick={() => {
                if (railingPts.length < 3) {
                  setError('Please place at least 3 floor boundary pins first (A, B, C, D).')
                  return
                }
                let nextZones = currentSlotData.markedZones || []
                if (railingPts.length >= 3 && (!nextZones || nextZones.length === 0)) {
                  nextZones = getDefaultPlantingZones()
                  const nextPhotos = [...roofPhotos]
                  nextPhotos[activeSlot] = { ...nextPhotos[activeSlot], markedZones: nextZones }
                  setRoofPhotos(nextPhotos)
                  syncPhotoToStructuralGrid(railingPts, nextZones)
                  setSelectedZoneTool('WALKWAY')
                }
                setError(null)
                setMarkupMode('zone')
              }}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                markupMode === 'zone'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              🎨 2. Zone Paint Tool
            </button>
          </div>
        </div>

        {/* Zone Tool Palette (shown in zone markup mode) */}
        {markupMode === 'zone' && (
          <div className="flex items-center gap-2 flex-wrap bg-slate-50 border border-slate-200 rounded-xl p-3">
            <span className="text-xs font-bold text-slate-600 mr-2">Select Zone Brush:</span>
            {ZONE_TOOLS.map(t => (
              <button
                key={t.id}
                type="button"
                onClick={() => setSelectedZoneTool(t.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                  selectedZoneTool === t.id
                    ? 'bg-white text-slate-900 shadow-sm ring-2 ring-emerald-500'
                    : 'bg-white/60 text-slate-600 hover:bg-white'
                }`}
              >
                <span className="h-3 w-3 rounded-full" style={{ backgroundColor: t.color }} />
                {t.label}
              </button>
            ))}
            <span className="text-[11px] text-emerald-800 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-lg ml-auto font-medium flex items-center gap-1.5">
              <span>💡</span>
              <span>All cells default to Planting (Full Sun). Just paint your walkways, obstacles, or shade.</span>
            </span>
          </div>
        )}

        {/* The Canvas Container without distortion */}
        <div
          style={{
            width: `min(100%, calc(80vh * ${aspect}))`,
            margin: '0 auto',
            aspectRatio: String(aspect),
          }}
          className="relative rounded-2xl overflow-hidden border border-slate-200 shadow-sm bg-slate-100"
        >
          <canvas
            ref={canvasRef}
            width={canvasDimensions.width}
            height={canvasDimensions.height}
            className="w-full h-full block"
            style={{
              cursor: isDraggingPin
                ? 'grabbing'
                : (hoveredPinIdx !== null ? 'grab' : (markupMode === 'railing' ? 'crosshair' : 'pointer'))
            }}
            onMouseDown={handleCanvasMouseDown}
            onMouseMove={handleCanvasMouseMove}
            onMouseUp={handleCanvasMouseUp}
            onMouseLeave={() => {
              if (draggingPinRef.current !== null) {
                draggingPinRef.current = null
                setIsDraggingPin(false)
              }
              isPaintingRef.current = false
              lastPaintedCellRef.current = null
              setHoveredPinIdx(null)
            }}
          />

          {/* Canvas Floating Toolbar */}
          <div className="absolute top-3 right-3 flex gap-2 z-10 flex-wrap">
            {markupMode === 'railing' && railingPts.length > 0 && (
              <>
                <button
                  type="button"
                  onClick={undoLastPin}
                  className="bg-white/95 backdrop-blur-xs text-slate-700 text-xs font-bold px-3 py-1.5 rounded-lg shadow hover:bg-white transition"
                >
                  ↩ Undo Last Pin
                </button>
                <button
                  type="button"
                  onClick={resetPins}
                  className="bg-white/95 backdrop-blur-xs text-red-600 text-xs font-bold px-3 py-1.5 rounded-lg shadow hover:bg-white flex items-center gap-1 transition"
                >
                  <Trash2 className="h-3 w-3" /> Clear / Reset Pins
                </button>
              </>
            )}

            {markupMode === 'zone' && (
              <button
                type="button"
                onClick={resetAllToPlanting}
                className="bg-white/95 backdrop-blur-xs text-emerald-700 hover:text-emerald-800 text-xs font-bold px-3 py-1.5 rounded-lg shadow hover:bg-white flex items-center gap-1.5 transition border border-emerald-200/60"
              >
                <RefreshCw className="h-3 w-3" /> Reset All to Planting
              </button>
            )}
          </div>
        </div>

        {/* Compact Footer Status Bar directly below Canvas Container */}
        {hasActivePhoto && (
          <div
            style={{
              width: `min(100%, calc(80vh * ${aspect}))`,
              margin: '0 auto',
            }}
            className="flex items-center justify-between flex-wrap gap-2 rounded-xl bg-slate-900 text-slate-200 px-4 py-2.5 text-xs font-medium shadow-xs"
          >
            <div className="flex items-center gap-2">
              <span className="font-bold text-white">{VIEW_SLOTS[activeSlot].edge}</span>
              <span className="text-slate-500">·</span>
              <span className="text-emerald-400 font-semibold">{railingPts.length} perimeter pins</span>
              <span className="text-slate-500">·</span>
              <span>{cellsList.length} mapped grid cells</span>
            </div>
            {railingPts.length > 0 && (
              <span className="text-amber-300 text-[11px] font-normal">
                💡 Drag pins A, B, C, D directly on the floor to adjust boundaries
              </span>
            )}
          </div>
        )}

        {/* Real-Time Structural Grid Metrics */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-center">
            <div className="text-[11px] text-slate-500 font-semibold uppercase">Total Area</div>
            <div className="text-lg font-bold text-slate-900 mt-0.5">
              {hasAnyPhoto ? `${width * depth} sq ft` : '0 sq ft'}
            </div>
            <div className="text-[10px] text-slate-400">
              {hasAnyPhoto ? `${width} × ${depth} ft` : 'Awaiting upload'}
            </div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-emerald-50/50 p-3 text-center">
            <div className="text-[11px] text-emerald-800 font-semibold uppercase">Planting Cells</div>
            <div className="text-lg font-bold text-emerald-700 mt-0.5">
              {hasAnyPhoto ? gardeningCount : 0}
            </div>
            <div className="text-[10px] text-emerald-600">
              {hasAnyPhoto ? (gardeningCount > 0 ? `${gardeningCount} cells painted` : 'None painted yet') : 'No photos mapped'}
            </div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-center">
            <div className="text-[11px] text-slate-500 font-semibold uppercase">Walkway Cells</div>
            <div className="text-lg font-bold text-slate-800 mt-0.5">
              {hasAnyPhoto ? walkwayCount : 0}
            </div>
            <div className="text-[10px] text-slate-400">
              {hasAnyPhoto ? (walkwayCount > 0 ? `${walkwayCount} cells painted` : 'None painted yet') : 'No photos mapped'}
            </div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-red-50/50 p-3 text-center">
            <div className="text-[11px] text-red-800 font-semibold uppercase">Obstacle Cells</div>
            <div className="text-lg font-bold text-red-700 mt-0.5">
              {hasAnyPhoto ? obstacleCount : 0}
            </div>
            <div className="text-[10px] text-red-600">
              {hasAnyPhoto ? (obstacleCount > 0 ? `${obstacleCount} cells marked` : 'None marked') : 'No obstacles'}
            </div>
          </div>
        </div>

        {error && (
          <div className="rounded-xl bg-red-50 border border-red-200 px-4 py-2 text-xs text-red-700 flex items-center gap-2">
            <ShieldAlert className="h-4 w-4 shrink-0 text-red-500" /> {error}
          </div>
        )}
      </div>

      {/* Nav Buttons */}
      <div className="flex justify-between items-center pt-2 flex-wrap gap-3">
        <button
          type="button"
          onClick={onBack}
          className="flex items-center gap-2 rounded-xl border border-slate-200 px-5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition"
        >
          <ChevronLeft className="h-4 w-4" /> Back to Preferences
        </button>

        <div className="flex items-center gap-3 flex-wrap">
          {hasActivePhoto && railingPts.length < 3 && (
            <span className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-2.5 py-1 font-medium flex items-center gap-1.5">
              <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-amber-600" />
              {VIEW_SLOTS[activeSlot].edge} needs pins ({railingPts.length}/4)
            </span>
          )}

          {hasNextView && (
            <button
              type="button"
              onClick={() => {
                if (gridCells && sessionId) {
                  saveCellConditions({ session_id: sessionId, cells: gridCells }).catch(() => {})
                }
                activateSlot(nextTargetSlot)
                setMarkupMode('railing')
                setError(null)
              }}
              className="flex items-center gap-2 rounded-xl border-2 border-emerald-600 bg-emerald-50 px-5 py-2.5 text-sm font-bold text-emerald-800 hover:bg-emerald-100 transition shadow-xs"
            >
              Save &amp; Next View ({VIEW_SLOTS[nextTargetSlot].edge})
              <ChevronRight className="h-4 w-4 text-emerald-600" />
            </button>
          )}

          <button
            type="button"
            onClick={handleSaveAndProceed}
            disabled={loading || !hasAnyPhoto}
            className="flex items-center gap-2 rounded-xl bg-emerald-600 px-6 py-2.5 text-sm font-semibold text-white shadow-md shadow-emerald-600/25 hover:bg-emerald-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
            title={!hasAnyPhoto ? "Please upload at least one rooftop photo" : ""}
          >
            {loading ? 'Saving Grid...' : (
              hasAnyPhoto
                ? `Generate Garden Design (Step 3) · ${markedCount}/${uploadedCount} marked`
                : 'Generate Photorealistic Garden Design'
            )}
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  )
}
