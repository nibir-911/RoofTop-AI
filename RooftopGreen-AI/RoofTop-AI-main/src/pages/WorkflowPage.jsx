import { motion, AnimatePresence } from 'framer-motion'
import { useState, useEffect } from 'react'
import { useAppStore } from '../store/useAppStore'
import Navbar from '../components/Navbar'
import PreferencesStep from './Preferences'
import RoofCapture from './RoofCapture'
import GardenDesign from './GardenDesign'
import GrowingGuide from './GrowingGuide'
import Suppliers from './Suppliers'
import PlantDoctor from './PlantDoctor'
import axios from 'axios'

const STEP_COMPONENTS = {
  1: PreferencesStep,
  2: RoofCapture,
  3: GardenDesign,
  4: GrowingGuide,
  5: Suppliers,
  6: PlantDoctor,
}
const STEP_LABELS = {
  1: 'Preferences',
  2: 'Roof Map',
  3: 'Garden Design',
  4: 'Growing Guide',
  5: 'Marketplace',
  6: 'Plant Doctor',
}

export default function WorkflowPage() {
  const { currentStep, setCurrentStep } = useAppStore()
  const [backendOk, setBackendOk] = useState(null)

  useEffect(() => {
    axios.get('/api/health', { timeout: 2000 })
      .then(() => setBackendOk(true))
      .catch(() => setBackendOk(false))
  }, [])

  const StepComp = STEP_COMPONENTS[currentStep] || PreferencesStep

  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar />
      {backendOk === false && (
        <div className="bg-amber-50 border-b border-amber-200 px-4 py-2 text-center text-sm text-amber-800">
          ⚠️ Running in demo mode — backend server not connected. Start the backend for full functionality.
        </div>
      )}
      <main className="mx-auto max-w-6xl px-4 py-6">
        <div className="mb-4 text-sm text-slate-500">
          Step {currentStep} of 6 —{' '}
          <span className="font-semibold text-slate-700">{STEP_LABELS[currentStep]}</span>
        </div>
        <AnimatePresence mode="wait">
          <motion.div
            key={currentStep}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.25 }}
          >
            <StepComp
              onNext={() => setCurrentStep(Math.min(6, currentStep + 1))}
              onBack={() => setCurrentStep(Math.max(1, currentStep - 1))}
            />
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  )
}
