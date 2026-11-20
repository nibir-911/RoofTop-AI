import { Leaf, LogOut, LayoutDashboard, ShoppingBag } from 'lucide-react'
import { useAppStore } from '../store/useAppStore'
import { Link, useNavigate, useLocation } from 'react-router-dom'

const STEPS = [
  { n: 1, label: 'Preferences' },
  { n: 2, label: 'Roof Map' },
  { n: 3, label: 'Garden Design' },
  { n: 4, label: 'Growing Guide' },
  { n: 5, label: 'Marketplace' },
  { n: 6, label: 'Plant Doctor' },
]

export default function Navbar() {
  const { user, isAuthenticated, logout, resetWorkflowState, currentStep, setCurrentStep } = useAppStore()
  const navigate = useNavigate()
  const location = useLocation()

  const handleLogout = () => {
    resetWorkflowState?.()
    logout()
    navigate('/')
  }

  const handleStepClick = (stepNum) => {
    setCurrentStep(stepNum)
    if (location.pathname !== '/workflow') {
      navigate('/workflow')
    }
  }

  return (
    <header className="sticky top-0 z-50 border-b border-emerald-100 bg-white/95 backdrop-blur-xl shadow-sm">
      <div className="mx-auto max-w-7xl flex items-center justify-between px-4 py-3 gap-4">
        <Link to="/" className="flex items-center gap-2 shrink-0 group">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-green-700 shadow-lg shadow-emerald-500/20 transition group-hover:scale-105">
            <Leaf className="h-5 w-5 text-white" />
          </div>
          <div>
            <span className="hidden sm:block font-bold text-slate-900 leading-tight">RooftopGreen AI</span>
            <span className="hidden sm:block text-[9px] uppercase tracking-wider text-emerald-700 font-semibold leading-none">6-Step Workflow</span>
          </div>
        </Link>

        {/* Step navigation pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto scrollbar-none flex-1 justify-center px-2">
          {STEPS.map((s) => {
            const isCurrent = location.pathname === '/workflow' && s.n === currentStep
            return (
              <button
                key={s.n}
                onClick={() => handleStepClick(s.n)}
                className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold whitespace-nowrap transition-all ${
                  isCurrent
                    ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/30'
                    : 'bg-slate-100 text-slate-600 hover:bg-emerald-50 hover:text-emerald-700'
                }`}
              >
                <span className={`flex h-4 w-4 items-center justify-center rounded-full text-[10px] ${
                  isCurrent ? 'bg-white/25 text-white' : 'bg-slate-200 text-slate-700'
                }`}>
                  {s.n}
                </span>
                <span className="hidden md:inline">{s.label}</span>
              </button>
            )
          })}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Link
            to="/dashboard"
            className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold transition ${
              location.pathname === '/dashboard'
                ? 'bg-slate-900 text-white'
                : 'border border-slate-200 text-slate-700 hover:bg-slate-100'
            }`}
          >
            <LayoutDashboard className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Dashboard</span>
          </Link>

          {isAuthenticated && (
            <div className="flex items-center gap-2">
              <span className="hidden lg:block text-xs font-medium text-slate-600">{user?.name}</span>
              <button
                onClick={handleLogout}
                title="Sign out"
                className="rounded-full border border-slate-200 p-2 text-slate-500 hover:text-red-500 hover:border-red-200 transition-colors"
              >
                <LogOut className="h-3.5 w-3.5" />
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
