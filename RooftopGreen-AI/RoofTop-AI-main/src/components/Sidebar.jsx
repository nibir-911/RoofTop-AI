import { useNavigate, useLocation } from 'react-router-dom'
import {
  Home,
  Trees,
  Gauge,
  ShoppingBag,
  BookOpen,
  Settings,
  Leaf,
  MapPin,
  Sparkles,
  Stethoscope,
  Compass,
} from 'lucide-react'
import { useAppStore } from '../store/useAppStore'

const NAV_ITEMS = [
  { label: 'Overview', icon: Home, path: '/dashboard', step: null },
  { label: 'Planner', icon: Trees, path: '/workflow', step: 1 },
  { label: 'Roof Map', icon: Compass, path: '/workflow', step: 2 },
  { label: 'Garden Design', icon: Sparkles, path: '/workflow', step: 3 },
  { label: 'Growing Guide', icon: BookOpen, path: '/workflow', step: 4 },
  { label: 'Marketplace', icon: ShoppingBag, path: '/workflow', step: 5 },
  { label: 'Plant Doctor', icon: Stethoscope, path: '/workflow', step: 6 },
  { label: 'Settings', icon: Settings, path: '/workflow', step: 1 },
]

export default function Sidebar({ className = '' }) {
  const navigate = useNavigate()
  const location = useLocation()
  const { currentStep, setCurrentStep } = useAppStore()

  const handleNav = (item) => {
    if (item.step !== null) {
      setCurrentStep(item.step)
    }
    navigate(item.path)
  }

  const isItemActive = (item) => {
    if (item.path === '/dashboard') {
      return location.pathname === '/dashboard'
    }
    if (location.pathname === '/workflow') {
      return item.step === currentStep
    }
    return false
  }

  return (
    <aside className={`w-72 shrink-0 rounded-[28px] border border-slate-200 bg-slate-900 p-5 text-white flex flex-col justify-between ${className}`}>
      <div>
        <div
          onClick={() => navigate('/')}
          className="flex items-center gap-3 border-b border-slate-700 pb-6 cursor-pointer group"
        >
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-500/20 text-emerald-300 transition group-hover:scale-105 group-hover:bg-emerald-500/30">
            <Leaf className="h-5 w-5" />
          </div>
          <div>
            <div className="font-bold text-white tracking-wide">RooftopGreen AI</div>
            <div className="text-[11px] text-emerald-400 uppercase tracking-wider font-semibold">Urban Garden Suite</div>
          </div>
        </div>

        <nav className="mt-6 space-y-1.5">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon
            const active = isItemActive(item)
            return (
              <button
                key={item.label}
                onClick={() => handleNav(item)}
                className={`flex w-full items-center justify-between rounded-2xl px-3.5 py-2.5 text-sm font-medium transition-all ${
                  active
                    ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-600/30 font-semibold'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`h-4 w-4 ${active ? 'text-white' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </div>
                {item.step && (
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                    active ? 'bg-white/20 text-white' : 'bg-slate-800 text-slate-400'
                  }`}>
                    Step {item.step}
                  </span>
                )}
              </button>
            )
          })}
        </nav>
      </div>

      <div className="mt-8 rounded-[24px] border border-slate-700/80 bg-slate-800/60 p-4">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-300">FastAPI Backend</span>
          <span className="rounded-full bg-emerald-500/20 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-emerald-400">
            Connected
          </span>
        </div>
        <p className="text-xs leading-5 text-slate-400">
          Plan, map, optimize, order materials, and diagnose crops seamlessly in one platform.
        </p>
      </div>
    </aside>
  )
}
