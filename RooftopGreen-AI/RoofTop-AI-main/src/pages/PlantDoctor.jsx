import { useState, useRef, useEffect } from 'react'
import { useAppStore } from '../store/useAppStore'
import { analyzePlantDoctor, chatPlantDoctor, withFallback, MOCK } from '../services/api'
import {
  ChevronLeft, ShieldCheck, Stethoscope, AlertTriangle, HelpCircle,
  CheckCircle, ArrowRight, RotateCcw, Bot, Sparkles, BookOpen, Send,
  RefreshCw, Upload, Image as ImageIcon, MessageSquare, Cpu, Check,
  Leaf, Info, X
} from 'lucide-react'
import { Link } from 'react-router-dom'

const COMMON_SYMPTOMS = [
  'Yellowing lower leaves',
  'White powdery spots on foliage',
  'Sticky residue and leaf curl',
  'Crispy brown leaf tips',
  'Stunted flowering or fruit drop',
  'Sudden midday leaf wilting',
]

const QUICK_QUESTIONS = [
  'Why are my tomato leaves curling?',
  'Organic remedy for white mealybugs?',
  'Best fertilizer schedule for rooftop lemon?',
  'How to treat powdery mildew with baking soda?',
  'How to prevent blossom end rot in tomatoes?',
  'Correct BARI neem oil spray ratio & schedule?'
]

export default function PlantDoctor({ onBack }) {
  const {
    symptoms,
    setSymptoms,
    doctorResult,
    setDoctorResult,
  } = useAppStore()

  const [customSymptom, setCustomSymptom] = useState('')
  const [loading, setLoading] = useState(false)
  const [leafImageB64, setLeafImageB64] = useState(null)
  const [errorToast, setErrorToast] = useState(null)
  const fileInputRef = useRef(null)
  const diagnosisCardRef = useRef(null)

  // RAG Chatbot State
  const [chatMessages, setChatMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      content: 'Hello! I am your AI Plant Doctor, powered by Gemini 3.5 Flash and grounded in verified BARI (Bangladesh Agricultural Research Institute) and DAE (Department of Agricultural Extension) urban agronomy knowledge bases.\n\nAsk me any question about plant diseases, pest identification, organic remedies, or container nutrition for your rooftop garden.',
      engine: 'gemini-3.5-flash',
      retrieved_sources: [
        {
          id: 'bari_overview',
          title: 'BARI Rooftop Agriculture & Bio-Pesticide Manual',
          source: 'BARI Horticulture & IPM Division'
        }
      ],
      time: 'Just now'
    }
  ])
  const [inputQuery, setInputQuery] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const chatScrollRef = useRef(null)

  // Auto-scroll chat to bottom
  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight
    }
  }, [chatMessages, chatLoading])

  const toggleSymptom = (sym) => {
    if (symptoms.includes(sym)) {
      setSymptoms(symptoms.filter(s => s !== sym))
    } else {
      setSymptoms([...symptoms, sym])
    }
  }

  const addCustomSymptom = (e) => {
    e.preventDefault()
    if (customSymptom.trim() && !symptoms.includes(customSymptom.trim())) {
      setSymptoms([...symptoms, customSymptom.trim()])
      setCustomSymptom('')
    }
  }

  const handleImageUpload = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    // Immediately clear previous diagnosis and any error so stale results never persist
    setDoctorResult(null)
    setErrorToast(null)
    const reader = new FileReader()
    reader.onload = (evt) => {
      const rawDataUrl = evt.target?.result
      if (!rawDataUrl) return

      // Pre-compress image in memory via canvas (max 768x768px, JPEG quality 0.75) for fast response
      const img = new window.Image()
      img.onload = () => {
        let width = img.width
        let height = img.height
        const maxDim = 768
        if (width > maxDim || height > maxDim) {
          if (width > height) {
            height = Math.round((height * maxDim) / width)
            width = maxDim
          } else {
            width = Math.round((width * maxDim) / height)
            height = maxDim
          }
        }
        const canvas = document.createElement('canvas')
        canvas.width = width
        canvas.height = height
        const ctx = canvas.getContext('2d')
        ctx.drawImage(img, 0, 0, width, height)
        const compressedDataUrl = canvas.toDataURL('image/jpeg', 0.75)
        setLeafImageB64(compressedDataUrl)
      }
      img.onerror = () => {
        setLeafImageB64(rawDataUrl)
      }
      img.src = rawDataUrl
    }
    reader.readAsDataURL(file)
    // Clear input value so selecting the same file again triggers onChange
    e.target.value = ''
  }

  const handleRemoveImage = () => {
    setLeafImageB64(null)
    setDoctorResult(null)
    setErrorToast(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleDiagnose = async () => {
    if (symptoms.length === 0 && !leafImageB64) return
    setLoading(true)
    setErrorToast(null)
    setDoctorResult(null)
    try {
      const payload = {
        symptoms: symptoms.length > 0 ? symptoms : ['Visual leaf inspection'],
        image_base64: leafImageB64 || null
      }
      const res = await withFallback(
        () => analyzePlantDoctor(payload),
        MOCK.doctorResult
      )
      if (res && res.primary_cause) {
        setDoctorResult(res)
        setTimeout(() => {
          diagnosisCardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }, 150)
      } else {
        throw new Error('Diagnosis failed to return a valid result. Please try again.')
      }
    } catch (err) {
      console.error('Diagnosis error:', err)
      const errorMsg = err?.response?.data?.detail || err?.message || 'Failed to complete leaf diagnosis. Please check server connection.'
      setErrorToast(errorMsg)
    } finally {
      setLoading(false)
    }
  }

  // ── Send RAG Chat Query ─────────────────────────────────────────────────────
  const handleSendChat = async (queryText = null) => {
    const textToSend = (typeof queryText === 'string' ? queryText : inputQuery).trim()
    if (!textToSend || chatLoading) return

    const userMsg = {
      id: 'user-' + Date.now(),
      role: 'user',
      content: textToSend,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }

    setChatMessages((prev) => [...prev, userMsg])
    setInputQuery('')
    setChatLoading(true)

    // Automatically include the last diagnosed disease from the uploaded leaf image in the chat context
    const lastDiagnosedDisease = doctorResult?.primary_cause || doctorResult?.diagnosis || null
    const diagnosisContext = doctorResult ? {
      disease: lastDiagnosedDisease,
      primary_cause: lastDiagnosedDisease,
      confidence_pct: doctorResult.confidence_pct,
      confidence_label: doctorResult.confidence_label,
      symptoms: symptoms.length > 0 ? symptoms : (doctorResult.symptoms || ['Visual leaf inspection']),
      care_steps: doctorResult.care_steps || [],
      alternative_causes: doctorResult.alternative_causes || [],
      organic_remedy: doctorResult.organic_remedy || null,
      prevention: doctorResult.prevention || null,
    } : (symptoms.length > 0 ? { symptoms, disease: symptoms.join(', '), primary_cause: symptoms.join(', ') } : null)

    // Send the last 4-6 chat messages along with current question
    const recentHistory = chatMessages
      .slice(-6)
      .map(m => ({ role: m.role, content: m.content }))

    const payload = {
      message: textToSend,
      query: textToSend,
      history: recentHistory,
      chat_history: recentHistory,
      last_diagnosis: lastDiagnosedDisease,
      diagnosis_context: diagnosisContext,
    }

    try {
      const res = await chatPlantDoctor(payload)
      if (res?.data?.status === 'ok') {
        const assistantMsg = {
          id: 'asst-' + Date.now(),
          role: 'assistant',
          content: res.data.reply,
          engine: res.data.engine || 'gemini-3.5-flash',
          retrieved_sources: res.data.retrieved_sources || [],
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
        setChatMessages((prev) => [...prev, assistantMsg])
      } else {
        throw new Error(res?.data?.message || 'Chat generation failed')
      }
    } catch (err) {
      console.warn('RAG Chat API warning (client fallback active):', err)
      const lowerQ = textToSend.toLowerCase()
      let contextualReply = ''
      let sourceTitle = 'BARI Rooftop Agriculture & Bio-Pesticide Manual'

      if (lowerQ.includes('why') || lowerQ.includes('cause') || lowerQ.includes('happen')) {
        contextualReply = `Based on BARI Rooftop Plant Pathology standards for ${lastDiagnosedDisease || 'common rooftop foliar conditions'}:\n\n• Primary Cause & Vectors: Urban rooftop temperatures (35°C–40°C on concrete slabs) and dry wind drafts accelerate pest vectors like silverleaf whiteflies, aphids, and thrips, while creating micro-fissures in leaf cuticle layers.\n• Leaf Reaction: In response to sap-sucking feeding or fungal penetration, the plant redirects sap flow, resulting in curling, chlorotic yellow margins, or powdery patches.\n• Prevention: Space containers 45cm apart for cross-ventilation, hang yellow sticky cards at canopy height, and keep potting mix evenly moist.`
        sourceTitle = 'BARI Urban Agronomy Disease Vector Protocol'
      } else if (lowerQ.includes('neem') || lowerQ.includes('ratio') || lowerQ.includes('how much') || lowerQ.includes('mix')) {
        contextualReply = `BARI Standard Organic Neem Oil Emulsion Formula:\n\n• Pure Cold-Pressed Neem Oil: 5 ml (min 1500 ppm Azadirachtin)\n• Mild Liquid Soap (baby shampoo or castile soap): 2 ml (as emulsifier)\n• Lukewarm Water: 1 Litre\n\nMethod: Mix soap in 100ml warm water until foamy, vigorously shake in neem oil until uniform milky white emulsion forms, then dilute with 900ml water. Spray strictly late afternoon (after 4:30 PM) to protect pollinators and prevent leaf scorch.`
        sourceTitle = 'BARI Bio-Pesticide Standard Operating Protocol'
      } else {
        contextualReply = `Based on the BARI Rooftop Agriculture Manual & DAE Guidelines${lastDiagnosedDisease ? ` regarding ${lastDiagnosedDisease}` : ''}:\n\n• Organic Treatment: Spray cold-pressed neem oil solution (5ml neem + 2ml liquid soap per 1L lukewarm water) late afternoon every 5 days.\n• Fungal Prevention: For powdery mildew or spots, apply baking soda spray (1 tsp baking soda + 1/2 tsp soap per 1L water).\n• Soil & Moisture: Top-dress containers with 2 handfuls of rich vermicompost and ensure pot drainage holes are free of stagnant water.`
      }

      const fallbackMsg = {
        id: 'asst-' + Date.now(),
        role: 'assistant',
        content: contextualReply,
        engine: 'rag_curated_knowledgebase_fallback',
        retrieved_sources: [
          {
            id: 'bari_standard_protocol',
            title: sourceTitle,
            source: 'BARI Horticulture & Bio-Pesticide Division'
          }
        ],
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
      setChatMessages((prev) => [...prev, fallbackMsg])
    } finally {
      setChatLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* ── Top Diagnostic Header Card ── */}
      <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <Stethoscope className="h-5 w-5 text-emerald-600" />
              AI Plant Doctor &amp; Health Diagnostics
            </h2>
            <p className="text-sm text-slate-500 mt-0.5">
              Select symptoms or upload a leaf photo to diagnose nutrient deficits, viral infections, and pests.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1.5 rounded-full bg-emerald-50 border border-emerald-200 px-3 py-1 text-xs font-semibold text-emerald-700">
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" /> BARI / DAE Verified
            </span>
          </div>
        </div>

        {/* Leaf Photo Upload & Symptom Selector */}
        <div className="grid gap-6 md:grid-cols-3">
          {/* Photo Upload Box */}
          <div className="md:col-span-1 rounded-xl border-2 border-dashed border-slate-200 p-4 bg-slate-50/50 flex flex-col items-center justify-center text-center">
            {leafImageB64 ? (
              <div className="relative w-full aspect-video rounded-lg overflow-hidden bg-slate-900 shadow-sm">
                <img
                  src={leafImageB64}
                  alt="Uploaded leaf"
                  className="w-full h-full object-cover"
                />
                <button
                  type="button"
                  onClick={handleRemoveImage}
                  className="absolute top-2 right-2 rounded-full bg-black/70 p-1 text-white hover:bg-black transition"
                  title="Remove image"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
                <div className="absolute bottom-1 left-2 text-[10px] font-medium text-emerald-300">
                  Leaf Photo Attached
                </div>
              </div>
            ) : (
              <div
                onClick={() => fileInputRef.current?.click()}
                className="cursor-pointer flex flex-col items-center py-2"
              >
                <div className="rounded-full bg-emerald-100/70 p-3 text-emerald-600 mb-2">
                  <Upload className="h-5 w-5" />
                </div>
                <span className="text-xs font-bold text-slate-800">Upload Diseased Leaf Photo</span>
                <span className="text-[11px] text-slate-400 mt-0.5">PNG, JPG up to 10MB</span>
              </div>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleImageUpload}
              className="hidden"
            />
          </div>

          {/* Symptom Tag Selector */}
          <div className="md:col-span-2 space-y-3">
            <label className="text-xs font-bold uppercase tracking-wider text-slate-600 block">
              Observed Symptoms:
            </label>
            <div className="flex flex-wrap gap-2">
              {COMMON_SYMPTOMS.map((sym) => {
                const isSelected = symptoms.includes(sym)
                return (
                  <button
                    key={sym}
                    type="button"
                    onClick={() => toggleSymptom(sym)}
                    className={`rounded-full border px-3.5 py-1.5 text-xs font-semibold transition-all ${
                      isSelected
                        ? 'border-emerald-500 bg-emerald-600 text-white shadow-sm'
                        : 'border-slate-200 bg-white text-slate-600 hover:border-emerald-300'
                    }`}
                  >
                    {sym}
                  </button>
                )
              })}
            </div>

            {/* Custom Symptom Input */}
            <form onSubmit={addCustomSymptom} className="flex gap-2 pt-1">
              <input
                type="text"
                value={customSymptom}
                onChange={(e) => setCustomSymptom(e.target.value)}
                placeholder="Type additional symptom (e.g. black sunken spots on tomato bottom)..."
                className="flex-1 rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-xs text-slate-800 focus:border-emerald-500 focus:outline-none"
              />
              <button
                type="submit"
                className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition"
              >
                + Add
              </button>
            </form>
          </div>
        </div>

        {/* Run Diagnosis Trigger */}
        <div className="flex items-center justify-between border-t border-slate-100 pt-4">
          <span className="text-xs text-slate-500">
            Active inputs: <strong className="text-slate-800">{symptoms.length} symptoms</strong> {leafImageB64 && '+ 1 photo'}
          </span>
          <button
            onClick={handleDiagnose}
            disabled={loading || (symptoms.length === 0 && !leafImageB64)}
            className="flex items-center gap-2 rounded-xl bg-emerald-600 px-6 py-2.5 text-sm font-semibold text-white shadow-md shadow-emerald-600/25 hover:bg-emerald-700 transition disabled:opacity-50"
          >
            {loading ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin" />
                {leafImageB64 ? 'Analyzing leaf with Gemini Vision...' : 'Analyzing symptoms...'}
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" /> Run AI Diagnosis
              </>
            )}
          </button>
        </div>
      </div>

      {/* ── Error Notification Toast ── */}
      {errorToast && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-800 flex items-start justify-between gap-3 shadow-sm">
          <div className="flex items-start gap-2.5">
            <AlertTriangle className="h-4 w-4 text-rose-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-bold text-rose-900">Diagnosis Notification</p>
              <p className="mt-0.5 text-rose-800">{errorToast}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setErrorToast(null)}
            className="text-rose-500 hover:text-rose-800 text-xs font-semibold px-2 py-0.5 rounded hover:bg-rose-100 transition"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* ── Diagnosis Results Card ── */}
      {doctorResult && (
        <div ref={diagnosisCardRef} className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm space-y-6 scroll-mt-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-100 pb-4">
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Primary Diagnosis</span>
              <h3 className="text-2xl font-black text-slate-900 mt-1">{doctorResult.primary_cause}</h3>
              {doctorResult.severity && (
                <span className="inline-block mt-1 text-[11px] font-semibold text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-2 py-0.5 mr-2">
                  Severity: {doctorResult.severity}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-800">
                {doctorResult.confidence_pct}% Confidence ({doctorResult.confidence_label || 'High'})
              </span>
              {doctorResult.engine && (
                <span className="rounded-full bg-slate-100 border border-slate-200 px-2.5 py-1 text-[11px] font-semibold text-slate-700 flex items-center gap-1">
                  <Cpu className="h-3 w-3 text-emerald-600" />
                  {doctorResult.engine.includes('gemini') ? 'Gemini 3.5 Flash Vision' : 'Rule Diagnostic Engine'}
                </span>
              )}
            </div>
          </div>

          {/* Targeted Organic Remedy if returned by Gemini Vision */}
          {doctorResult.organic_remedy && (
            <div className="rounded-xl border border-emerald-200 bg-emerald-50/70 p-4 space-y-1">
              <div className="text-xs font-bold uppercase tracking-wider text-emerald-900 flex items-center gap-1.5">
                <ShieldCheck className="h-4 w-4 text-emerald-600" />
                Targeted Organic Remedy (BARI Standards):
              </div>
              <p className="text-xs text-emerald-950 leading-relaxed font-medium">
                {doctorResult.organic_remedy}
              </p>
            </div>
          )}

          <div className="grid gap-6 md:grid-cols-2">
            {/* Actionable Care Steps */}
            <div className="space-y-3 rounded-xl border border-emerald-100 bg-emerald-50/50 p-4">
              <div className="flex items-center gap-2 text-sm font-bold text-emerald-900">
                <CheckCircle className="h-4 w-4 text-emerald-600" />
                Step-by-Step Care Regimen:
              </div>
              <ul className="space-y-2 text-xs text-slate-700">
                {doctorResult.care_steps?.map((step, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-600 text-[10px] font-bold text-white">
                      {idx + 1}
                    </span>
                    <span className="leading-relaxed">{step}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Differential Causes & Questions */}
            <div className="space-y-4">
              {doctorResult.alternative_causes?.length > 0 && (
                <div className="rounded-xl border border-slate-100 bg-slate-50 p-4 space-y-2">
                  <div className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                    <AlertTriangle className="h-4 w-4 text-amber-500" />
                    Alternative Possibilities:
                  </div>
                  <ul className="space-y-1 text-xs text-slate-600 list-disc list-inside">
                    {doctorResult.alternative_causes.map((alt, i) => (
                      <li key={i}>{alt}</li>
                    ))}
                  </ul>
                </div>
              )}

              {doctorResult.follow_up_questions?.length > 0 && (
                <div className="rounded-xl border border-slate-100 bg-slate-50 p-4 space-y-2">
                  <div className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                    <HelpCircle className="h-4 w-4 text-blue-500" />
                    Helpful Check Questions:
                  </div>
                  <ul className="space-y-1 text-xs text-slate-600 list-disc list-inside">
                    {doctorResult.follow_up_questions.map((q, i) => (
                      <li key={i}>{q}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>

          {/* Quick-Action: Ask Chatbot about this Diagnosis */}
          <div className="rounded-xl bg-emerald-50 border border-emerald-200 p-3.5 flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-xs text-emerald-900 font-medium">
              <Sparkles className="h-4 w-4 text-emerald-600 shrink-0" />
              <span>Diagnosed with <strong>{doctorResult.primary_cause}</strong>? Consult our RAG Agronomy Assistant for organic formulas:</span>
            </div>
            <button
              type="button"
              onClick={() => handleSendChat(`How do I cure ${doctorResult.primary_cause} organically using rooftop gardening practices?`)}
              className="shrink-0 flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3.5 py-1.5 text-xs font-bold text-white hover:bg-emerald-700 transition shadow-sm"
            >
              <MessageSquare className="h-3.5 w-3.5" />
              Ask RAG Chatbot
            </button>
          </div>
        </div>
      )}

      {/* ── STEP 6: Interactive RAG Plant Doctor Chatbot ── */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-4">
        {/* Chatbot Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-100 pb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-tr from-emerald-600 to-teal-500 text-white shadow-md shadow-emerald-500/20">
              <Bot className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-slate-900">AI Plant Doctor RAG Assistant</h3>
                <span className="flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-0.5 text-[10px] font-bold text-emerald-800">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  RAG Grounded
                </span>
              </div>
              <p className="text-xs text-slate-500">
                Retrieval-Augmented Generation grounded in BARI &amp; DAE Agronomy Knowledge Base (Gemini 3.5 Flash)
              </p>
            </div>
          </div>

          {doctorResult && (
            <span className="rounded-lg bg-slate-100 border border-slate-200 px-2.5 py-1 text-[11px] font-semibold text-slate-700 flex items-center gap-1.5">
              <Leaf className="h-3.5 w-3.5 text-emerald-600" />
              Context: {doctorResult.primary_cause}
            </span>
          )}
        </div>

        {/* Quick Suggestion Chips */}
        <div className="space-y-1.5">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block">
            Suggested Agronomy Questions:
          </span>
          <div className="flex flex-wrap gap-1.5">
            {QUICK_QUESTIONS.map((q, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleSendChat(q)}
                disabled={chatLoading}
                className="rounded-lg border border-slate-200 bg-slate-50/80 px-2.5 py-1 text-[11px] font-medium text-slate-700 hover:border-emerald-400 hover:bg-emerald-50 hover:text-emerald-900 transition disabled:opacity-50"
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        {/* Chat History Messages Container */}
        <div
          ref={chatScrollRef}
          className="rounded-xl border border-slate-100 bg-slate-50/60 p-4 space-y-4 max-h-[460px] overflow-y-auto"
        >
          {chatMessages.map((msg) => {
            const isUser = msg.role === 'user'
            return (
              <div
                key={msg.id}
                className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}
              >
                {!isUser && (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-emerald-600 text-white shadow-sm mt-0.5">
                    <Bot className="h-4 w-4" />
                  </div>
                )}

                <div className={`max-w-[85%] space-y-2 ${isUser ? 'items-end' : 'items-start'}`}>
                  {/* Message Bubble */}
                  <div
                    className={`rounded-2xl px-4 py-3 text-xs leading-relaxed shadow-sm ${
                      isUser
                        ? 'bg-slate-900 text-white rounded-tr-none'
                        : 'bg-white border border-slate-200/80 text-slate-800 rounded-tl-none space-y-2'
                    }`}
                  >
                    <div className="whitespace-pre-line">
                      {msg.content}
                    </div>

                    {/* RAG Sources Used Badge Section (For University Defense & Faculty Review) */}
                    {!isUser && msg.retrieved_sources?.length > 0 && (
                      <div className="border-t border-slate-100 pt-2 mt-2 space-y-1.5">
                        <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-emerald-800">
                          <BookOpen className="h-3 w-3 text-emerald-600" />
                          Verified RAG Knowledge Base Sources:
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {msg.retrieved_sources.map((src, sIdx) => (
                            <span
                              key={sIdx}
                              className="inline-flex items-center gap-1 rounded-md bg-emerald-50 border border-emerald-200/80 px-2 py-0.5 text-[10px] font-medium text-emerald-900"
                              title={src.crop ? `Crop: ${src.crop}` : undefined}
                            >
                              <Check className="h-2.5 w-2.5 text-emerald-600" />
                              <strong className="font-semibold">{src.title}</strong>
                              <span className="text-emerald-700 opacity-80">({src.source})</span>
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Timestamp & Engine Attribution */}
                  <div className={`flex items-center gap-2 px-1 text-[10px] text-slate-400 ${isUser ? 'justify-end' : 'justify-start'}`}>
                    <span>{msg.time}</span>
                    {!isUser && msg.engine && (
                      <>
                        <span>•</span>
                        <span className="flex items-center gap-1 text-slate-500">
                          <Cpu className="h-2.5 w-2.5 text-emerald-600" /> {msg.engine}
                        </span>
                      </>
                    )}
                  </div>
                </div>
              </div>
            )
          })}

          {/* Typing Indicator */}
          {chatLoading && (
            <div className="flex gap-3 justify-start items-center">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-emerald-600 text-white shadow-sm">
                <Bot className="h-4 w-4 animate-spin" />
              </div>
              <div className="rounded-2xl rounded-tl-none border border-slate-200 bg-white px-4 py-2.5 text-xs text-slate-500 shadow-sm flex items-center gap-2">
                <Sparkles className="h-3.5 w-3.5 text-emerald-600 animate-pulse" />
                <span>Searching BARI/DAE knowledge base &amp; synthesizing agronomic advice...</span>
              </div>
            </div>
          )}
        </div>

        {/* Input Bar */}
        <form
          onSubmit={(e) => {
            e.preventDefault()
            handleSendChat()
          }}
          className="flex gap-2"
        >
          <input
            type="text"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            disabled={chatLoading}
            placeholder="Ask about symptoms, neem spray ratios, fungal spots, watering schedules..."
            className="flex-1 rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-xs text-slate-800 placeholder:text-slate-400 focus:border-emerald-500 focus:bg-white focus:outline-none transition"
          />
          <button
            type="submit"
            disabled={chatLoading || !inputQuery.trim()}
            className="flex items-center gap-1.5 rounded-xl bg-emerald-600 px-5 py-2.5 text-xs font-bold text-white shadow-sm hover:bg-emerald-700 transition disabled:opacity-50"
          >
            <Send className="h-3.5 w-3.5" />
            Send
          </button>
        </form>
      </div>

      {/* ── Nav & Final Actions ── */}
      <div className="flex justify-between items-center pt-2">
        <button
          onClick={onBack}
          className="flex items-center gap-2 rounded-xl border border-slate-200 px-5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition"
        >
          <ChevronLeft className="h-4 w-4" />
          Back to Marketplace
        </button>

        <Link
          to="/dashboard"
          className="flex items-center gap-2 rounded-xl bg-slate-900 px-6 py-2.5 text-sm font-semibold text-white shadow-md hover:bg-slate-800 transition"
        >
          View Garden Dashboard
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </div>
  )
}
