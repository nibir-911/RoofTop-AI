import { useState, useEffect, useMemo, useRef } from 'react'
import { useAppStore } from '../store/useAppStore'
import { calculateMaterials, getPlants, getGuide, withFallback, MOCK } from '../services/api'
import {
  ChevronRight,
  ChevronLeft,
  Calendar,
  ShieldCheck,
  Scale,
  ShoppingCart,
  Check,
  Info,
  RefreshCw,
  Sparkles,
  AlertTriangle,
  Leaf,
  Layers
} from 'lucide-react'

const VARIANT_OPTIONS = [
  { id: 'Productive', label: 'Productive (Edibles)', desc: 'Maximized vegetables & culinary herbs' },
  { id: 'Colorful', label: 'Colorful (Aesthetic)', desc: 'Flowering blooms & ornamental foliage' },
  { id: 'Balanced', label: 'Balanced Oasis', desc: 'Harmonious edible & flower companion mix' }
]

export default function GrowingGuide({ onNext, onBack }) {
  const {
    sessionId,
    selectedVariant,
    selectedLayout,
    setSelectedVariant,
    setSelectedLayout,
    grid,
    gridCells,
    roofDimensions,
    preferences,
    budget: storeBudget,
    gardenLayouts,
    bom,
    setBom,
    structuralLoad,
    setStructuralLoad,
    addRecommendedToCart,
  } = useAppStore()

  // Support both selectedLayout and selectedVariant naming
  const activeVariant = selectedLayout || selectedVariant || 'Balanced'
  const activeGrid = grid || gridCells || {}
  const plannedBudget = Number(storeBudget ?? preferences?.budget ?? preferences?.budget_bdt ?? 15000)

  const [loading, setLoading] = useState(false)
  const [addedCart, setAddedCart] = useState(false)
  const [selectedPlantId, setSelectedPlantId] = useState('tomato')
  const [plantGuide, setPlantGuide] = useState(null)
  const [plantsList, setPlantsList] = useState([])
  const isInitialMount = useRef(true)

  // 1. Reactive calculation of gardening plant count from grid & layouts
  const { plantCount, gardeningCellsCount, totalRoofAreaSqft } = useMemo(() => {
    const cells = Object.values(activeGrid)
    const gardeningCells = cells.filter(c => c.zone === 'GARDENING' || (!c.zone && c.status !== 'BLOCKED'))
    const cellCount = gardeningCells.length > 0 ? gardeningCells.length : 12

    // If gardenLayouts has exact placements for current variant, prioritize that
    const placements = gardenLayouts?.[activeVariant]?.placements
    const finalCount = (placements && placements.length > 0) ? placements.length : cellCount

    const width = roofDimensions?.width_ft || 20
    const depth = roofDimensions?.depth_ft || 15
    const areaSqft = width * depth

    return {
      plantCount: Math.max(finalCount, 4),
      gardeningCellsCount: cellCount,
      totalRoofAreaSqft: areaSqft
    }
  }, [activeGrid, gardenLayouts, activeVariant, roofDimensions])

  // 2. Reactive client-side calculation of BOM & Structural Load (Instant zero-delay update)
  const reactiveCalculation = useMemo(() => {
    let planterDivisor = 1.4
    let unitPlantCost = 35.0

    if (activeVariant === 'Productive') {
      planterDivisor = 1.3
      unitPlantCost = 30.0
    } else if (activeVariant === 'Colorful') {
      planterDivisor = 1.6
      unitPlantCost = 45.0
    } else {
      planterDivisor = 1.4
      unitPlantCost = 38.0
    }

    const plantersNeeded = Math.max(1, Math.ceil(plantCount / 4))
    const soilLitres = plantersNeeded * 25
    const dripUnits = plantersNeeded
    const drainTrays = plantersNeeded

    const items = [
      {
        description: '2×2 ft UV-Treated Planter Box',
        name: '2×2 ft UV-Treated Planter Box',
        item: '2×2 ft UV-Treated Planter Box',
        product_name: '2×2 ft UV-Treated Planter Box',
        qty: plantersNeeded,
        quantity: plantersNeeded,
        count: plantersNeeded,
        unit: 'piece',
        price_unit: 'piece',
        unit_price: 480.0,
        unit_cost_bdt: 480.0,
        price_bdt: 480.0,
        price: 480.0,
        total: plantersNeeded * 480.0,
        total_bdt: plantersNeeded * 480.0,
        cost: plantersNeeded * 480.0
      },
      {
        description: 'Sterilized Light Organic Soil Mix',
        name: 'Sterilized Light Organic Soil Mix',
        item: 'Sterilized Light Organic Soil Mix',
        product_name: 'Sterilized Light Organic Soil Mix',
        qty: soilLitres,
        quantity: soilLitres,
        count: soilLitres,
        unit: 'litre',
        price_unit: 'litre',
        unit_price: 10.0,
        unit_cost_bdt: 10.0,
        price_bdt: 10.0,
        price: 10.0,
        total: soilLitres * 10.0,
        total_bdt: soilLitres * 10.0,
        cost: soilLitres * 10.0
      },
      {
        description: 'Drip Irrigation Tube & Emitters',
        name: 'Drip Irrigation Tube & Emitters',
        item: 'Drip Irrigation Tube & Emitters',
        product_name: 'Drip Irrigation Tube & Emitters',
        qty: dripUnits,
        quantity: dripUnits,
        count: dripUnits,
        unit: 'unit',
        price_unit: 'unit',
        unit_price: 140.0,
        unit_cost_bdt: 140.0,
        price_bdt: 140.0,
        price: 140.0,
        total: dripUnits * 140.0,
        total_bdt: dripUnits * 140.0,
        cost: dripUnits * 140.0
      },
      {
        description: 'Heavy Duty Poly Drainage Tray',
        name: 'Heavy Duty Poly Drainage Tray',
        item: 'Heavy Duty Poly Drainage Tray',
        product_name: 'Heavy Duty Poly Drainage Tray',
        qty: drainTrays,
        quantity: drainTrays,
        count: drainTrays,
        unit: 'piece',
        price_unit: 'piece',
        unit_price: 110.0,
        unit_cost_bdt: 110.0,
        price_bdt: 110.0,
        price: 110.0,
        total: drainTrays * 110.0,
        total_bdt: drainTrays * 110.0,
        cost: drainTrays * 110.0
      },
      {
        description: `Selected ${activeVariant} Saplings & Rootstocks`,
        name: `Selected ${activeVariant} Saplings & Rootstocks`,
        item: `Selected ${activeVariant} Saplings & Rootstocks`,
        product_name: `Selected ${activeVariant} Saplings & Rootstocks`,
        qty: plantCount,
        quantity: plantCount,
        count: plantCount,
        unit: 'sapling',
        price_unit: 'sapling',
        unit_price: unitPlantCost,
        unit_cost_bdt: unitPlantCost,
        price_bdt: unitPlantCost,
        price: unitPlantCost,
        total: plantCount * unitPlantCost,
        total_bdt: plantCount * unitPlantCost,
        cost: plantCount * unitPlantCost
      }
    ]

    const subtotal = items.reduce((sum, it) => sum + it.total_bdt, 0)
    const labour = Math.round(subtotal * 0.12)
    const total = subtotal + labour

    const userBudget = plannedBudget

    // Structural load calculation:
    // Total wet weight in kg: planters + wet soil (~0.95 kg/L) + plants + water
    const areaM2 = Math.max(totalRoofAreaSqft * 0.092903, 8.0)
    const totalWetMassKg = (plantersNeeded * 3.5) + (soilLitres * 0.95) + (plantCount * 2.2) + (dripUnits * 0.8)
    const avgLoad = Math.round((totalWetMassKg / areaM2) * 10) / 10
    const peakLoad = Math.round((avgLoad * 1.48) * 10) / 10

    const limitKgM2 = preferences?.load_limit_kg_m2 || 150.0
    const loadStatus = peakLoad < (limitKgM2 * 0.8) ? 'SAFE' : (peakLoad <= limitKgM2 ? 'CAUTION' : 'WARNING')

    return {
      items,
      subtotal_bdt: subtotal,
      subtotal: subtotal,
      labour_bdt: labour,
      labour: labour,
      total_bdt: total,
      total: total,
      grand_total: total,
      budget_bdt: Number(userBudget),
      planter_boxes: plantersNeeded,
      planters_needed: plantersNeeded,
      structural_load: {
        avg_kg_m2: avgLoad,
        peak_kg_m2: peakLoad,
        status: loadStatus,
        limit_kg_m2: limitKgM2,
        disclaimer: 'STRUCTURAL SAFETY DISCLAIMER: These are estimated wet-load figures based on lightweight potting mix and planter distributed density. A qualified structural engineer should be consulted before major installations.'
      }
    }
  }, [plantCount, activeVariant, totalRoofAreaSqft, preferences, plannedBudget])

  // 3. Keep store in sync reactively with calculated BOM
  useEffect(() => {
    setBom({
      items: reactiveCalculation.items,
      subtotal_bdt: reactiveCalculation.subtotal_bdt,
      labour_bdt: reactiveCalculation.labour_bdt,
      total_bdt: reactiveCalculation.total_bdt,
      budget_bdt: plannedBudget,
      structural_load: reactiveCalculation.structural_load
    })
    setStructuralLoad(reactiveCalculation.structural_load)
  }, [reactiveCalculation, plannedBudget, setBom, setStructuralLoad])

  // 4. Synchronize with backend API whenever layout/variant, grid, or preferences change
  useEffect(() => {
    let isCancelled = false

    const syncBackend = async () => {
      setLoading(true)
      try {
        const matRes = await withFallback(
          () => calculateMaterials({
            session_id: sessionId || 'demo-session',
            variant: activeVariant,
            plant_count: plantCount,
            roof_area_sqft: totalRoofAreaSqft,
            budget: plannedBudget,
            budget_bdt: plannedBudget,
          }),
          reactiveCalculation
        )
        if (!isCancelled && matRes) {
          setBom(matRes)
          if (matRes.structural_load) {
            setStructuralLoad(matRes.structural_load)
          }
        }
      } catch (err) {
        console.warn('Backend sync failed, using reactive client calculation', err)
      } finally {
        if (!isCancelled) setLoading(false)
      }
    }

    syncBackend()

    return () => {
      isCancelled = true
    }
  }, [activeVariant, activeGrid, preferences, sessionId, plantCount, totalRoofAreaSqft, plannedBudget])

  // 5. Dynamic Seasonal Planting Guide data tailored to active layout variant
  const seasonalGuideData = useMemo(() => {
    if (activeVariant === 'Productive') {
      return {
        theme: 'High-Yield Urban Kitchen Crop Schedule',
        plants: [
          { id: 'tomato', name_en: 'Tomato (Toma-to)', tag: 'Heavy Sun' },
          { id: 'chilli', name_en: 'Green Chilli (Morich)', tag: 'Full Sun' },
          { id: 'spinach', name_en: 'Spinach (Palong Shak)', tag: 'Quick Harvest' },
          { id: 'mint', name_en: 'Mint (Pudina)', tag: 'Moisture Lover' },
          { id: 'coriander', name_en: 'Coriander (Dhone Pata)', tag: 'Salad Herb' },
          { id: 'brinjal', name_en: 'Eggplant (Begun)', tag: 'High Yield' },
        ],
        seasons: [
          {
            season: 'Winter / Rabi (Oct - Feb)',
            icon: '❄️',
            badge: 'Peak Harvest',
            action: 'Sow tomatoes, spinach, carrots & winter chillies. Direct rooftop sun is mild and optimal. Top-dress with 1 cup vermicompost every 14 days.'
          },
          {
            season: 'Pre-Monsoon / Summer (Mar - May)',
            icon: '☀️',
            badge: 'Heat Protection',
            action: 'Chaitra sun is intense. Mulch topsoil with 2 inches of dried leaves or coco chips. Water twice daily early morning & sunset.'
          },
          {
            season: 'Monsoon / Kharif-2 (Jun - Sep)',
            icon: '🌧️',
            badge: 'Drainage Alert',
            action: 'Clear all planter drain trays. Shift tender herbs under parapet overhang. Inspect foliage after heavy downpours for fungal spots.'
          }
        ]
      }
    } else if (activeVariant === 'Colorful') {
      return {
        theme: 'Vibrant Floral & Pollinator Calendar',
        plants: [
          { id: 'marigold', name_en: 'Marigold (Genda)', tag: 'Pest Barrier' },
          { id: 'rose', name_en: 'Miniature Rose (Golap)', tag: 'Sun Perennial' },
          { id: 'bougainvillea', name_en: 'Bougainvillea (Kagoj Ful)', tag: 'Drought Hardy' },
          { id: 'jasmine', name_en: 'Arabian Jasmine (Beli)', tag: 'Fragrant' },
          { id: 'hibiscus', name_en: 'Hibiscus (Jaba)', tag: 'Pollinator Magnet' },
          { id: 'portulaca', name_en: 'Portulaca (Time Ful)', tag: 'Railing Trailing' },
        ],
        seasons: [
          {
            season: 'Winter Blooming (Nov - Feb)',
            icon: '🌸',
            badge: 'Peak Bloom',
            action: 'Prime season for Marigolds, Petunias, and Roses. Deadhead spent blossoms weekly to trigger continuous flower bud formation.'
          },
          {
            season: 'Summer Radiance (Mar - May)',
            icon: '☀️',
            badge: 'Hydration',
            action: 'Bougainvillea and Portulaca thrive in extreme terrace heat. Mist jasmine foliage in evenings to preserve sweet fragrance.'
          },
          {
            season: 'Monsoon Foliage (Jun - Sep)',
            icon: '🌧️',
            badge: 'Vigorous Growth',
            action: 'Prune leggy stems. Ensure pots are elevated on drainage blocks so water drains freely during torrential Dhaka rainstorms.'
          }
        ]
      }
    } else {
      // Balanced
      return {
        theme: 'Integrated Companion Ecosystem Calendar',
        plants: [
          { id: 'tomato', name_en: 'Tomato', tag: 'Productive' },
          { id: 'marigold', name_en: 'Marigold', tag: 'Companion Deterrent' },
          { id: 'chilli', name_en: 'Green Chilli', tag: 'Kitchen Staple' },
          { id: 'mint', name_en: 'Mint & Basil', tag: 'Aromatic' },
          { id: 'lemon', name_en: 'Kagzi Lemon', tag: 'Container Shrub' },
          { id: 'spinach', name_en: 'Leafy Greens', tag: 'Daily Nutrition' },
        ],
        seasons: [
          {
            season: 'Winter / Rabi (Oct - Feb)',
            icon: '🌱',
            badge: 'Companion Synergy',
            action: 'Plant Marigolds around Tomato planter edges to repel nematodes and whiteflies. Excellent cool-season vegetable and herb yields.'
          },
          {
            season: 'Summer Management (Mar - May)',
            icon: '☀️',
            badge: 'Microclimate',
            action: 'Group containers together to create a humid microclimate. Use taller lemon shrubs to filter harsh western sunlight for sensitive mint.'
          },
          {
            season: 'Monsoon / Kharif (Jun - Sep)',
            icon: '🌧️',
            badge: 'Resilience',
            action: 'Heavy rain provides natural nitrogen wash. Check root aerations and apply organic neem cake powder to prevent root rot.'
          }
        ]
      }
    }
  }, [activeVariant])

  // Load specific plant guide when selected
  useEffect(() => {
    const fetchPlantGuide = async () => {
      try {
        const guideRes = await withFallback(
          () => getGuide(selectedPlantId),
          {
            plant: { name_en: selectedPlantId.replace('_', ' ').toUpperCase(), name_bn: '' },
            care_guide: {
              sunlight_req: 'Requires 5-8 hours direct rooftop sun daily.',
              watering_schedule: 'Water daily in early morning. Keep container soil moist but well-drained.',
              soil_and_fertilizer: 'Lightweight potting mix with 40% organic vermicompost.',
              pest_prevention: 'Apply diluted organic neem oil spray every 10 days.',
            },
            seasonal_calendar: seasonalGuideData.seasons
          }
        )
        setPlantGuide(guideRes)
      } catch (err) {
        console.error(err)
      }
    }
    fetchPlantGuide()
  }, [selectedPlantId, seasonalGuideData])

  const handleVariantSwitch = (vId) => {
    if (setSelectedLayout) setSelectedLayout(vId)
    if (setSelectedVariant) setSelectedVariant(vId)
  }

  const currentBom = bom || reactiveCalculation
  const currentLoad = structuralLoad || reactiveCalculation.structural_load

  // Safely normalize every BOM item so all keys exist with robust fallbacks
  const normalizedBomItems = useMemo(() => {
    const rawItems = currentBom?.items || reactiveCalculation?.items || []
    return rawItems.map((item, index) => {
      const description = item.description || item.item || item.name || item.product_name || `Garden Material ${index + 1}`
      const qty = Math.max(1, Math.round(Number(item.qty ?? item.quantity ?? item.count ?? 1)))
      const unit = item.unit || item.price_unit || (description.toLowerCase().includes('soil') ? 'litre' : (description.toLowerCase().includes('sapling') ? 'sapling' : 'piece'))
      let unit_price = Number(item.unit_price ?? item.unit_cost_bdt ?? item.price_bdt ?? item.price ?? 0)
      if (unit_price <= 0) {
        const lowerDesc = description.toLowerCase()
        if (lowerDesc.includes('planter')) unit_price = 480.0
        else if (lowerDesc.includes('soil')) unit_price = 10.0
        else if (lowerDesc.includes('drip') || lowerDesc.includes('irrigation')) unit_price = 140.0
        else if (lowerDesc.includes('drainage') || lowerDesc.includes('tray')) unit_price = 110.0
        else if (lowerDesc.includes('sapling') || lowerDesc.includes('plant') || lowerDesc.includes('seed')) unit_price = 35.0
        else if (lowerDesc.includes('fertilizer') || lowerDesc.includes('compost')) unit_price = 40.0
        else unit_price = 150.0
      }
      const total = Number(item.total ?? item.total_bdt ?? item.cost ?? (qty * unit_price)) || (qty * unit_price)
      return {
        description,
        name: description,
        item: description,
        product_name: description,
        qty,
        quantity: qty,
        count: qty,
        unit,
        price_unit: unit,
        unit_price,
        unit_cost_bdt: unit_price,
        price_bdt: unit_price,
        price: unit_price,
        total,
        total_bdt: total,
        cost: total,
      }
    })
  }, [currentBom, reactiveCalculation])

  // Proper planter box count from BOM or mapped cells (Math.max(1, Math.ceil(plantPositions / 4)))
  const planterBoxesCount = useMemo(() => {
    if (currentBom?.planter_boxes) return Number(currentBom.planter_boxes)
    if (currentBom?.planters_needed) return Number(currentBom.planters_needed)
    const planterItem = normalizedBomItems.find(it => it.description.toLowerCase().includes('planter'))
    if (planterItem) return planterItem.qty
    return Math.max(1, Math.ceil(plantCount / 4))
  }, [currentBom, normalizedBomItems, plantCount])

  // Subtotal, Labour, and Grand Total calculated accurately from visible rows
  const bomFinancials = useMemo(() => {
    const subtotal = normalizedBomItems.reduce((sum, it) => sum + it.total, 0)
    const labour = Number(currentBom?.labour_bdt ?? currentBom?.labour ?? Math.round(subtotal * 0.12))
    const total = subtotal + labour
    const budget = plannedBudget
    const diff = budget - total
    return {
      subtotal,
      labour,
      total,
      budget,
      diff,
      isUnder: diff >= 0,
      pctUsed: Math.min(Math.round((total / (budget || 1)) * 100), 100)
    }
  }, [normalizedBomItems, currentBom, plannedBudget])

  const handleAddToCart = () => {
    addRecommendedToCart(normalizedBomItems)
    setAddedCart(true)
    setTimeout(() => setAddedCart(false), 2200)
  }

  return (
    <div className="space-y-6">
      {/* Dynamic Variant Switcher Pill Header */}
      <div className="rounded-2xl border border-emerald-100 bg-white p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-700">
                Live Reactive Optimization Engine
              </span>
            </div>
            <h2 className="text-xl font-bold text-slate-900 mt-0.5">Growing Guide &amp; Dynamic BOM</h2>
            <p className="text-xs text-slate-500">
              Synced with Grid ({gardeningCellsCount} gardening cells, {totalRoofAreaSqft} sq ft) &amp; layout variant.
            </p>
          </div>

          <div className="flex items-center gap-2">
            {loading && (
              <span className="flex items-center gap-1.5 text-xs text-slate-400">
                <RefreshCw className="h-3.5 w-3.5 animate-spin text-emerald-600" /> Syncing...
              </span>
            )}
            <div className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-800 border border-emerald-200">
              Variant: {activeVariant}
            </div>
          </div>
        </div>

        {/* Quick layout switcher tabs right on this page */}
        <div className="grid gap-2 sm:grid-cols-3 pt-1">
          {VARIANT_OPTIONS.map((v) => {
            const isSelected = activeVariant === v.id
            return (
              <button
                key={v.id}
                onClick={() => handleVariantSwitch(v.id)}
                className={`flex flex-col text-left rounded-xl p-3 border transition-all ${
                  isSelected
                    ? 'border-emerald-500 bg-emerald-50/70 shadow-sm ring-1 ring-emerald-500'
                    : 'border-slate-200 bg-slate-50/50 hover:bg-white hover:border-emerald-300'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className={`text-xs font-bold ${isSelected ? 'text-emerald-800' : 'text-slate-800'}`}>
                    {v.label}
                  </span>
                  {isSelected && <Check className="h-3.5 w-3.5 text-emerald-600" />}
                </div>
                <span className="text-[11px] text-slate-500 mt-1 leading-snug">{v.desc}</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Bill of Materials (BOM) Table */}
      <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Layers className="h-5 w-5 text-emerald-600" />
              <h3 className="font-bold text-slate-900">Calculated Bill of Materials (BOM)</h3>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Dynamically scales with {plantCount} plant positions across {planterBoxesCount} planter boxes.
            </p>
          </div>

          <button
            onClick={handleAddToCart}
            className={`flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition shadow-sm ${
              addedCart
                ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                : 'bg-emerald-600 text-white hover:bg-emerald-700 shadow-emerald-600/25'
            }`}
          >
            {addedCart ? <Check className="h-4 w-4" /> : <ShoppingCart className="h-4 w-4" />}
            {addedCart ? 'Added to Cart!' : 'Add Materials to Cart'}
          </button>
        </div>

        {/* Budget comparison banner */}
        <div className="rounded-xl bg-slate-50 border border-slate-200/80 p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
          <div>
            <span className="text-slate-500">Planned Budget: </span>
            <span className="font-bold text-slate-800">৳{bomFinancials.budget.toLocaleString()}</span>
            <span className="mx-2 text-slate-300">|</span>
            <span className="text-slate-500">Estimated Total: </span>
            <span className="font-bold text-emerald-700">৳{bomFinancials.total.toLocaleString()}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className={`font-semibold px-2.5 py-0.5 rounded-full ${
              bomFinancials.isUnder ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
            }`}>
              {bomFinancials.isUnder
                ? `৳${bomFinancials.diff.toLocaleString()} within budget`
                : `৳${Math.abs(bomFinancials.diff).toLocaleString()} over budget`}
            </span>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-100 text-xs font-semibold uppercase text-slate-400">
              <tr>
                <th className="py-2.5">Item Description</th>
                <th className="py-2.5">Qty</th>
                <th className="py-2.5">Unit</th>
                <th className="py-2.5 text-right">Unit Price</th>
                <th className="py-2.5 text-right">Total (BDT)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700 text-xs sm:text-sm">
              {normalizedBomItems.map((item, i) => (
                <tr key={i} className="hover:bg-slate-50/60 transition-colors">
                  <td className="py-2.5 font-medium text-slate-900">{item.description}</td>
                  <td className="py-2.5 font-semibold text-emerald-700">{item.qty}</td>
                  <td className="py-2.5 text-slate-500 capitalize">{item.unit}</td>
                  <td className="py-2.5 text-right text-slate-600">৳{Number(item.unit_price).toLocaleString()}</td>
                  <td className="py-2.5 text-right font-bold text-slate-800">৳{Number(item.total).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
            <tfoot className="border-t-2 border-slate-100 text-xs sm:text-sm">
              <tr>
                <td colSpan={4} className="py-2 text-right font-medium text-slate-500">Materials Subtotal:</td>
                <td className="py-2 text-right font-bold text-slate-900">৳{bomFinancials.subtotal.toLocaleString()}</td>
              </tr>
              <tr>
                <td colSpan={4} className="py-1 text-right text-slate-500">Labour &amp; Rooftop Setup (12%):</td>
                <td className="py-1 text-right font-medium text-slate-700">৳{bomFinancials.labour.toLocaleString()}</td>
              </tr>
              <tr className="text-sm sm:text-base border-t border-slate-100">
                <td colSpan={4} className="py-2.5 text-right font-bold text-emerald-900">Grand Total:</td>
                <td className="py-2.5 text-right font-black text-emerald-700 text-base sm:text-lg">
                  ৳{bomFinancials.total.toLocaleString()}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* Structural Load Calculation & Safety Assessment */}
      <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <Scale className="h-5 w-5 text-emerald-600" />
            <h3 className="font-bold text-slate-900">Structural Wet-Load Safety Verification</h3>
          </div>
          <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider ${
            currentLoad.status === 'SAFE'
              ? 'bg-emerald-100 text-emerald-800'
              : currentLoad.status === 'CAUTION'
                ? 'bg-amber-100 text-amber-800'
                : 'bg-red-100 text-red-800'
          }`}>
            Safety Status: {currentLoad.status}
          </span>
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-xl bg-slate-50/80 p-4 border border-slate-200">
            <span className="text-xs text-slate-500 font-medium">Estimated Avg Wet Load</span>
            <div className="mt-1 text-2xl font-black text-slate-900">{currentLoad.avg_kg_m2} kg/m²</div>
            <span className="text-[11px] text-slate-400">Evenly distributed across roof area</span>
          </div>

          <div className="rounded-xl bg-slate-50/80 p-4 border border-slate-200">
            <span className="text-xs text-slate-500 font-medium">Estimated Peak Wet Load</span>
            <div className={`mt-1 text-2xl font-black ${
              currentLoad.status === 'SAFE' ? 'text-emerald-700' : 'text-amber-600'
            }`}>
              {currentLoad.peak_kg_m2} kg/m²
            </div>
            <span className="text-[11px] text-slate-400">Concentrated weight beneath planters</span>
          </div>

          <div className="rounded-xl bg-slate-50/80 p-4 border border-slate-200">
            <span className="text-xs text-slate-500 font-medium">Rooftop Structural Threshold</span>
            <div className="mt-1 text-2xl font-black text-slate-900">
              {currentLoad.limit_kg_m2 || 150.0} kg/m²
            </div>
            <span className="text-[11px] text-emerald-600 font-semibold">Standard concrete rooftop safe</span>
          </div>
        </div>

        {/* Load Bar visualization */}
        <div className="space-y-1.5 pt-1">
          <div className="flex justify-between text-xs text-slate-600">
            <span>Peak Wet Load vs Maximum Capacity</span>
            <span className="font-bold">
              {Math.round(((currentLoad.peak_kg_m2 || 50) / (currentLoad.limit_kg_m2 || 150)) * 100)}% of limit
            </span>
          </div>
          <div className="h-2.5 w-full rounded-full bg-slate-100 overflow-hidden">
            <div
              className={`h-full transition-all duration-500 rounded-full ${
                currentLoad.status === 'SAFE'
                  ? 'bg-emerald-500'
                  : currentLoad.status === 'CAUTION'
                    ? 'bg-amber-500'
                    : 'bg-red-500'
              }`}
              style={{
                width: `${Math.min(
                  Math.round(((currentLoad.peak_kg_m2 || 50) / (currentLoad.limit_kg_m2 || 150)) * 100),
                  100
                )}%`
              }}
            />
          </div>
        </div>

        <div className="rounded-xl bg-amber-50/80 p-3.5 border border-amber-200 text-xs text-amber-900 leading-relaxed flex items-start gap-2">
          <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
          <span>{currentLoad.disclaimer}</span>
        </div>
      </div>

      {/* Dynamic Seasonal Planting Guide */}
      <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-100 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <Calendar className="h-5 w-5 text-emerald-600" />
              <h3 className="font-bold text-slate-900">Seasonal Planting Routine &amp; Care</h3>
            </div>
            <p className="text-xs text-slate-500 mt-1">{seasonalGuideData.theme} (Dhaka Climate)</p>
          </div>

          {/* Plant chip selector */}
          <div className="flex flex-wrap gap-1.5">
            {seasonalGuideData.plants.map((p) => (
              <button
                key={p.id}
                onClick={() => setSelectedPlantId(p.id)}
                className={`flex items-center gap-1 rounded-full px-3 py-1 text-xs font-semibold transition ${
                  selectedPlantId === p.id
                    ? 'bg-emerald-600 text-white shadow-sm'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                <span>{p.name_en}</span>
                <span className="text-[9px] opacity-75 font-normal">({p.tag})</span>
              </button>
            ))}
          </div>
        </div>

        {/* Seasonal timeline cards */}
        <div className="grid gap-4 md:grid-cols-3">
          {seasonalGuideData.seasons.map((s, idx) => (
            <div key={idx} className="rounded-xl border border-slate-200/80 bg-slate-50/60 p-4 space-y-2 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-base">{s.icon}</span>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-100">
                    {s.badge}
                  </span>
                </div>
                <h4 className="font-bold text-xs text-slate-900 mt-2">{s.season}</h4>
                <p className="text-xs text-slate-600 mt-2 leading-relaxed">{s.action}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Detailed plant care card */}
        {plantGuide && (
          <div className="rounded-xl border border-emerald-100 bg-emerald-50/40 p-4 space-y-3.5">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
              <div className="flex items-center gap-2">
                <Leaf className="h-4 w-4 text-emerald-700 shrink-0" />
                <h4 className="text-xs font-bold text-emerald-950 uppercase tracking-wider">
                  Specific Care Guide: {plantGuide.plant?.name_en}
                  {plantGuide.plant?.name_bn ? ` (${plantGuide.plant.name_bn})` : ''}
                  {plantGuide.plant?.scientific_name ? (
                    <span className="italic font-serif font-normal normal-case text-emerald-800 ml-1.5 text-[11px]">
                      • {plantGuide.plant.scientific_name}
                    </span>
                  ) : ''}
                </h4>
              </div>
              {plantGuide.plant?.rooftop_suitability && (
                <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border self-start sm:self-auto ${
                  plantGuide.plant.rooftop_suitability === 'Suitable'
                    ? 'bg-emerald-100 text-emerald-800 border-emerald-200'
                    : 'bg-amber-100 text-amber-800 border-amber-200'
                }`}>
                  Rooftop: {plantGuide.plant.rooftop_suitability}
                </span>
              )}
            </div>

            {/* Subtle Verified Source Badge with Citation */}
            {(plantGuide.care_guide?.is_verified || plantGuide.plant?.is_verified || plantGuide.care_guide?.source_title || plantGuide.plant?.source_title) && (
              <div className="flex flex-wrap items-center justify-between gap-2 bg-white/95 border border-emerald-200/90 rounded-lg px-3 py-2 text-xs shadow-xs">
                <div className="flex items-center gap-1.5 text-emerald-950 flex-wrap">
                  <div className="flex items-center gap-1 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200 text-emerald-800 font-bold text-[10px] uppercase tracking-wider shrink-0">
                    <ShieldCheck className="h-3 w-3 text-emerald-600" />
                    Verified Source
                  </div>
                  <span className="font-semibold text-slate-800">
                    {plantGuide.care_guide?.source_title || plantGuide.plant?.source_title || 'DAE / BARI Rooftop Agriculture Manual'}
                  </span>
                  {(plantGuide.care_guide?.source_page || plantGuide.plant?.source_page) && (
                    <span className="text-slate-500 text-[11px]">
                      • {plantGuide.care_guide?.source_page || plantGuide.plant?.source_page}
                    </span>
                  )}
                </div>
                {(plantGuide.care_guide?.source_url || plantGuide.plant?.source_url) && (
                  <a
                    href={plantGuide.care_guide?.source_url || plantGuide.plant?.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 font-semibold text-emerald-700 hover:text-emerald-900 underline text-[11px] shrink-0"
                  >
                    View Source Citation &rarr;
                  </a>
                )}
              </div>
            )}

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 text-xs text-slate-700">
              <div className="bg-white/80 p-2.5 rounded-lg border border-emerald-100/60">
                <strong className="text-emerald-900 block mb-1">☀️ Sunlight Exposure:</strong>
                {plantGuide.care_guide?.sunlight_req}
              </div>
              <div className="bg-white/80 p-2.5 rounded-lg border border-emerald-100/60">
                <strong className="text-emerald-900 block mb-1">💧 Irrigation Schedule:</strong>
                {plantGuide.care_guide?.watering_schedule}
              </div>
              <div className="bg-white/80 p-2.5 rounded-lg border border-emerald-100/60">
                <strong className="text-emerald-900 block mb-1">🌱 Soil &amp; Nutrient Feeding:</strong>
                {plantGuide.care_guide?.soil_and_fertilizer}
              </div>
              <div className="bg-white/80 p-2.5 rounded-lg border border-emerald-100/60">
                <strong className="text-emerald-900 block mb-1">🪴 Pot &amp; Spacing:</strong>
                {plantGuide.care_guide?.container_recommendation || 'Standard 10-14 inch depth planter or geobag with drainage holes.'}
              </div>
              <div className="bg-white/80 p-2.5 rounded-lg border border-emerald-100/60">
                <strong className="text-emerald-900 block mb-1">🛡️ Pest &amp; Fungal Defense:</strong>
                {plantGuide.care_guide?.pest_prevention}
              </div>
              <div className="bg-white/80 p-2.5 rounded-lg border border-emerald-100/60">
                <strong className="text-emerald-900 block mb-1">🌾 Harvest &amp; Growth:</strong>
                {plantGuide.care_guide?.harvest_tips || 'Harvest regularly in the morning to encourage vigorous ongoing growth.'}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Nav Buttons */}
      <div className="flex justify-between items-center pt-2">
        <button
          onClick={onBack}
          className="flex items-center gap-2 rounded-xl border border-slate-200 px-5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition"
        >
          <ChevronLeft className="h-4 w-4" />
          Back to Garden Design
        </button>
        <button
          onClick={onNext}
          className="flex items-center gap-2 rounded-xl bg-emerald-600 px-6 py-2.5 text-sm font-semibold text-white shadow-md shadow-emerald-600/25 hover:bg-emerald-700 transition"
        >
          Proceed to Marketplace
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
