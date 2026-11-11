import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  ArrowRight,
  BarChart3,
  Bell,
  BookOpen,
  Bot,
  CheckCircle2,
  ChevronRight,
  CloudSun,
  Droplets,
  Gauge,
  Heart,
  Home,
  Leaf,
  LayoutGrid,
  LogOut,
  MapPin,
  Menu,
  Search,
  Settings,
  ShieldCheck,
  ShoppingBag,
  Sparkles,
  Sprout,
  Star,
  SunMedium,
  Trees,
} from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Link, NavLink, Route, Routes, useNavigate } from 'react-router-dom'
import { toast } from 'react-hot-toast'
import { useAppStore } from './store/useAppStore'

const features = [
  { icon: LayoutGrid, title: 'Smart Rooftop Planning', text: 'Design a productive layout based on sunlight, water, shade, structure, and budget.' },
  { icon: Sparkles, title: 'AI Plant Recommendations', text: 'Get tailored plant pairings for your rooftop climate, style, and goals.' },
  { icon: ShieldCheck, title: 'AI Plant Doctor', text: 'Diagnose nutrient issues, disease symptoms, and watering imbalances in seconds.' },
  { icon: ShoppingBag, title: 'Smart Gardening Marketplace', text: 'Buy high-performing planters, soil, irrigation tools, and rooftop-ready essentials.' },
  { icon: Bot, title: 'Personalized Gardening Assistant', text: 'Receive reminders, task flows, and weekly care recommendations from your AI garden coach.' },
]

const steps = [
  'Tell us about your rooftop.',
  'Get your personalized gardening plan.',
  'Discover suitable plants.',
  'Shop gardening essentials.',
  'Grow healthier plants with AI assistance.',
]

const inspirations = [
  { title: 'Sunset Terrace', location: 'Brooklyn, NY', image: 'https://images.unsplash.com/photo-1466692476868-aef1dfb1e735?auto=format&fit=crop&w=900&q=80', stats: '340 sq ft • 24 varieties' },
  { title: 'Urban Soil Lab', location: 'Chicago, IL', image: 'https://images.unsplash.com/photo-1501004318641-b39e6451bec6?auto=format&fit=crop&w=900&q=80', stats: '510 sq ft • 18 varieties' },
  { title: 'Herb Canopy', location: 'Austin, TX', image: 'https://images.unsplash.com/photo-1466692476868-aef1dfb1e735?auto=format&fit=crop&w=900&q=80', stats: '290 sq ft • 12 edible rows' },
]

const plantCards = [
  { name: 'Tomato Tower', sunlight: 'Full sun', care: 'High yield', accent: 'bg-emerald-100 text-emerald-700' },
  { name: 'Lavender Border', sunlight: 'Partial sun', care: 'Low water', accent: 'bg-violet-100 text-violet-700' },
  { name: 'Herb Spiral', sunlight: 'Sun + shade', care: 'Compact', accent: 'bg-amber-100 text-amber-700' },
  { name: 'Lettuce Bed', sunlight: 'Filtered sun', care: 'Fast harvest', accent: 'bg-rose-100 text-rose-700' },
]

const marketplaceItems = [
  { name: 'Smart Drip Kit', price: '$118', note: 'Water-efficient irrigation' },
  { name: 'Grow Bag Bundle', price: '$72', note: 'For herbs & greens' },
  { name: 'Planter Rail Set', price: '$195', note: 'Vertical garden ready' },
]

const testimonials = [
  { name: 'Mila R.', quote: 'RoofTop AI transformed our cracked terrace into a lush micro-farm. The recommendations were specific and surprisingly practical.', rating: 5 },
  { name: 'Daniel S.', quote: 'The plant doctor caught a nutrient imbalance before our greens started yellowing. That saved the entire crop.', rating: 5 },
  { name: 'Aisha P.', quote: 'We launched a rooftop herb garden in two weeks and the layout plan made it feel effortless.', rating: 5 },
]

const faqs = [
  { q: 'Can I plan a rooftop without prior gardening experience?', a: 'Absolutely. RoofTop AI helps beginners with step-by-step guidance and layout suggestions built around your rooftop conditions.' },
  { q: 'Does the planner factor in weight limits and drainage?', a: 'Yes. The planner considers structure, drainage, water access, and weight capacity to recommend safe and sustainable layouts.' },
  { q: 'Can I shop for tools and planters inside the app?', a: 'Yes. The marketplace brings together rooftop-ready equipment, planters, soil kits, and irrigation essentials.' },
  { q: 'Is this suitable for small urban rooftops?', a: 'Definitely. The AI can optimize compact spaces with container clusters, vertical planters, and low-maintenance options.' },
]

const healthData = [
  { month: 'Jan', yield: 38, moisture: 58 },
  { month: 'Feb', yield: 48, moisture: 64 },
  { month: 'Mar', yield: 58, moisture: 68 },
  { month: 'Apr', yield: 72, moisture: 71 },
  { month: 'May', yield: 88, moisture: 74 },
  { month: 'Jun', yield: 96, moisture: 77 },
]

const productivityData = [
  { name: 'Herbs', value: 30 },
  { name: 'Greens', value: 25 },
  { name: 'Flowers', value: 20 },
  { name: 'Fruit', value: 25 },
]

const dashboardCards = [
  { label: 'Garden health', value: '92%', icon: Heart },
  { label: 'Water efficiency', value: '78%', icon: Droplets },
  { label: 'Sun coverage', value: '84%', icon: SunMedium },
  { label: 'Yield forecast', value: '$1.8k', icon: BarChart3 },
]

const plannerSchema = z.object({
  rooftopSize: z.string().min(1, 'Please enter your rooftop size'),
  rooftopType: z.string().min(1),
  shape: z.string().min(1),
  orientation: z.string().min(1),
  sunlight: z.string().min(1),
  waterSource: z.string().min(1),
  weightCapacity: z.string().min(1),
  budget: z.string().min(1),
  style: z.string().min(1),
  purpose: z.string().min(1),
})

const signupSchema = z.object({
  name: z.string().min(2, 'Name is required'),
  email: z.string().email('Enter a valid email'),
  password: z.string().min(8, 'Use at least 8 characters'),
})

const loginSchema = z.object({
  email: z.string().email('Enter a valid email'),
  password: z.string().min(8, 'Use at least 8 characters'),
})

function App() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<AuthPage mode="login" />} />
        <Route path="/signup" element={<AuthPage mode="signup" />} />
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route path="/planner" element={<PlannerPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
      </Routes>
    </div>
  )
}

function HomePage() {
  return (
    <div className="bg-white">
      <header className="sticky top-0 z-50 border-b border-emerald-100/80 bg-white/80 backdrop-blur-xl">
        <nav className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4 lg:px-8">
          <Link to="/" className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-500 to-green-700 shadow-lg shadow-emerald-500/20">
              <Leaf className="h-5 w-5 text-white" />
            </div>
            <div>
              <div className="text-lg font-semibold text-slate-900">RoofTop AI</div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500">smart gardening</div>
            </div>
          </Link>

          <div className="hidden items-center gap-8 text-sm font-medium text-slate-600 md:flex">
            <a href="#features" className="transition hover:text-emerald-600">Features</a>
            <a href="#how-it-works" className="transition hover:text-emerald-600">How it works</a>
            <a href="#marketplace" className="transition hover:text-emerald-600">Marketplace</a>
            <a href="#faq" className="transition hover:text-emerald-600">FAQ</a>
          </div>

          <div className="flex items-center gap-3">
            <button className="hidden rounded-full border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 md:inline-flex">
              <Bell className="mr-2 h-4 w-4" /> Alerts
            </button>
            <Link to="/login" className="rounded-full border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-semibold text-emerald-700 transition hover:bg-emerald-100">Log in</Link>
            <Link to="/signup" className="rounded-full bg-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-emerald-600/30 transition hover:bg-emerald-700">Start Your Garden</Link>
          </div>
        </nav>
      </header>

      <main>
        <section className="relative overflow-hidden bg-gradient-to-br from-emerald-50 via-lime-50 to-white">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(34,197,94,0.12),transparent_30%),radial-gradient(circle_at_bottom_right,_rgba(16,185,129,0.12),transparent_35%)]" />
          <div className="relative mx-auto grid max-w-7xl gap-12 px-6 py-16 lg:grid-cols-2 lg:px-8 lg:py-24">
            <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }} className="flex flex-col justify-center">
              <div className="mb-4 inline-flex w-fit items-center rounded-full border border-emerald-200 bg-white/80 px-3 py-1 text-sm font-medium text-emerald-700 shadow-sm">
                <Sparkles className="mr-2 h-4 w-4" /> AI-powered rooftop optimization
              </div>
              <h1 className="max-w-xl text-4xl font-black tracking-tight text-slate-900 sm:text-5xl lg:text-6xl">
                Turn Your Rooftop Into a Thriving Green Paradise
              </h1>
              <p className="mt-6 max-w-xl text-lg leading-8 text-slate-600">
                Design a sustainable, high-yield rooftop garden with custom solar planning, plant intelligence, marketplace tools, and a live gardening assistant built for modern urban living.
              </p>

              <div className="mt-8 flex flex-wrap items-center gap-4">
                <Link to="/signup" className="inline-flex items-center rounded-full bg-emerald-600 px-6 py-3 font-semibold text-white shadow-xl shadow-emerald-600/30 transition hover:bg-emerald-700">
                  Start Your Garden <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
                <a href="#features" className="inline-flex items-center rounded-full border border-slate-300 bg-white px-6 py-3 font-semibold text-slate-700 transition hover:border-emerald-200 hover:text-emerald-700">
                  Explore Features
                </a>
              </div>

              <div className="mt-10 grid gap-4 sm:grid-cols-3">
                <div className="rounded-2xl border border-slate-200 bg-white/80 p-4 shadow-sm">
                  <div className="text-3xl font-bold text-slate-900">2.4x</div>
                  <div className="mt-1 text-sm text-slate-600">Faster planning</div>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-white/80 p-4 shadow-sm">
                  <div className="text-3xl font-bold text-slate-900">4.9/5</div>
                  <div className="mt-1 text-sm text-slate-600">User satisfaction</div>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-white/80 p-4 shadow-sm">
                  <div className="text-3xl font-bold text-slate-900">89%</div>
                  <div className="mt-1 text-sm text-slate-600">Plant survival</div>
                </div>
              </div>
            </motion.div>

            <motion.div initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.6 }} className="relative">
              <div className="relative overflow-hidden rounded-[32px] border border-emerald-100 bg-gradient-to-br from-emerald-100 via-white to-lime-50 p-4 shadow-[0_30px_80px_rgba(15,23,42,0.12)]">
                <div className="overflow-hidden rounded-[28px] bg-slate-200">
                  <img
                    src="https://images.unsplash.com/photo-1501004318641-b39e6451bec6?auto=format&fit=crop&w=1200&q=80"
                    alt="Rooftop garden"
                    className="h-[560px] w-full object-cover"
                  />
                </div>
                <div className="absolute -bottom-6 left-6 rounded-3xl border border-emerald-100 bg-white/90 p-4 shadow-xl backdrop-blur-sm">
                  <div className="mb-2 flex items-center justify-between">
                    <span className="text-sm font-semibold text-slate-800">AI Rooftop Analysis</span>
                    <span className="rounded-full bg-emerald-100 px-2 py-1 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-700">live</span>
                  </div>
                  <div className="space-y-3">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-700"><SunMedium className="h-5 w-5" /></div>
                      <div>
                        <div className="text-sm font-semibold text-slate-800">Sun Exposure</div>
                        <div className="text-xs text-slate-500">6.5 hours / day</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-amber-100 text-amber-700"><Droplets className="h-5 w-5" /></div>
                      <div>
                        <div className="text-sm font-semibold text-slate-800">Watering</div>
                        <div className="text-xs text-slate-500">Drip line recommended</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        </section>

        <section id="features" className="mx-auto max-w-7xl px-6 py-20 lg:px-8">
          <div className="mb-12 text-center">
            <div className="mb-4 text-sm font-semibold uppercase tracking-[0.2em] text-emerald-600">Features</div>
            <h2 className="text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">Everything your rooftop garden needs</h2>
          </div>
          <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-5">
            {features.map(({ icon: Icon, title, text }) => (
              <motion.div whileHover={{ y: -4 }} key={title} className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm shadow-slate-200/60">
                <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-700">
                  <Icon className="h-5 w-5" />
                </div>
                <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
                <p className="mt-3 text-sm leading-6 text-slate-600">{text}</p>
              </motion.div>
            ))}
          </div>
        </section>

        <section id="how-it-works" className="bg-slate-50 py-20">
          <div className="mx-auto max-w-7xl px-6 lg:px-8">
            <div className="mb-12 text-center">
              <div className="mb-4 text-sm font-semibold uppercase tracking-[0.2em] text-emerald-600">How it works</div>
              <h2 className="text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">From rooftop blank space to thriving ecosystem</h2>
            </div>
            <div className="grid gap-6 md:grid-cols-5">
              {steps.map((step, index) => (
                <div key={step} className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
                  <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-full bg-emerald-600 text-sm font-bold text-white">{index + 1}</div>
                  <p className="text-base font-medium text-slate-700">{step}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-6 py-20 lg:px-8">
          <div className="mb-10 flex items-end justify-between gap-4">
            <div>
              <div className="mb-3 text-sm font-semibold uppercase tracking-[0.2em] text-emerald-600">Inspiration</div>
              <h2 className="text-3xl font-bold tracking-tight text-slate-900">Featured rooftop garden inspirations</h2>
            </div>
            <Link to="/planner" className="hidden items-center gap-2 text-sm font-semibold text-emerald-700 md:inline-flex">
              Design your own <ChevronRight className="h-4 w-4" />
            </Link>
          </div>
          <div className="grid gap-6 lg:grid-cols-3">
            {inspirations.map((item) => (
              <div key={item.title} className="overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-sm">
                <img src={item.image} alt={item.title} className="h-72 w-full object-cover" />
                <div className="p-5">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xl font-semibold text-slate-900">{item.title}</h3>
                    <span className="rounded-full bg-emerald-100 px-2 py-1 text-xs font-semibold text-emerald-700">Featured</span>
                  </div>
                  <div className="mt-3 flex items-center gap-2 text-sm text-slate-500"><MapPin className="h-4 w-4" /> {item.location}</div>
                  <p className="mt-4 text-sm text-slate-600">{item.stats}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="bg-gradient-to-br from-emerald-50 via-white to-lime-50 py-20">
          <div className="mx-auto max-w-7xl px-6 lg:px-8">
            <div className="mb-12 text-center">
              <div className="mb-3 text-sm font-semibold uppercase tracking-[0.2em] text-emerald-600">Popular plants</div>
              <h2 className="text-3xl font-bold tracking-tight text-slate-900">The plants that thrive on rooftops</h2>
            </div>
            <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
              {plantCards.map((plant) => (
                <div key={plant.name} className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-sm">
                  <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-700">
                    <Leaf className="h-6 w-6" />
                  </div>
                  <div className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${plant.accent}`}>{plant.sunlight}</div>
                  <h3 className="mt-4 text-xl font-semibold text-slate-900">{plant.name}</h3>
                  <p className="mt-2 text-sm text-slate-600">Care profile: {plant.care}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-6 py-20 lg:px-8">
          <div className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
            <div className="rounded-[28px] border border-slate-200 bg-white p-8 shadow-sm">
              <div className="mb-4 text-sm font-semibold uppercase tracking-[0.2em] text-emerald-600">AI Plant Doctor</div>
              <h2 className="text-3xl font-bold tracking-tight text-slate-900">Spot stress before it spreads</h2>
              <div className="mt-6 space-y-4">
                <div className="flex items-center justify-between rounded-2xl bg-slate-50 p-4">
                  <div>
                    <div className="text-sm font-medium text-slate-500">Leaf yellowing</div>
                    <div className="mt-1 font-semibold text-slate-900">Possible nitrogen deficiency</div>
                  </div>
                  <div className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-700">Low confidence</div>
                </div>
                <div className="flex items-center justify-between rounded-2xl bg-slate-50 p-4">
                  <div>
                    <div className="text-sm font-medium text-slate-500">Watering pattern</div>
                    <div className="mt-1 font-semibold text-slate-900">Needs 20% less irrigation</div>
                  </div>
                  <div className="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-semibold text-emerald-700">Optimized</div>
                </div>
                <div className="flex items-center justify-between rounded-2xl bg-slate-50 p-4">
                  <div>
                    <div className="text-sm font-medium text-slate-500">Daily care reminder</div>
                    <div className="mt-1 font-semibold text-slate-900">Rotate herbs for even growth</div>
                  </div>
                  <div className="rounded-full bg-sky-100 px-2.5 py-1 text-xs font-semibold text-sky-700">Action</div>
                </div>
              </div>
            </div>

            <div id="marketplace" className="rounded-[28px] border border-slate-200 bg-slate-900 p-8 text-white shadow-sm">
              <div className="mb-4 text-sm font-semibold uppercase tracking-[0.2em] text-emerald-300">Marketplace</div>
              <h2 className="text-3xl font-bold tracking-tight text-white">Smart essentials for elevated rooftop living</h2>
              <div className="mt-6 space-y-4">
                {marketplaceItems.map((item) => (
                  <div key={item.name} className="flex items-center justify-between rounded-2xl border border-slate-700 bg-slate-800/60 p-4">
                    <div>
                      <div className="font-semibold text-white">{item.name}</div>
                      <div className="text-sm text-slate-300">{item.note}</div>
                    </div>
                    <div className="text-right">
                      <div className="font-bold text-emerald-300">{item.price}</div>
                      <div className="text-xs text-slate-400">Free shipping</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="bg-slate-50 py-20">
          <div className="mx-auto max-w-7xl px-6 lg:px-8">
            <div className="mb-10 text-center">
              <div className="mb-3 text-sm font-semibold uppercase tracking-[0.2em] text-emerald-600">Testimonials</div>
              <h2 className="text-3xl font-bold tracking-tight text-slate-900">Customers growing greener with RoofTop AI</h2>
            </div>
            <div className="grid gap-6 md:grid-cols-3">
              {testimonials.map((t) => (
                <div key={t.name} className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm">
                  <div className="mb-4 flex gap-1 text-amber-400">
                    {Array.from({ length: t.rating }).map((_, index) => (
                      <Star key={index} className="h-4 w-4 fill-current" />
                    ))}
                  </div>
                  <p className="text-base leading-7 text-slate-700">“{t.quote}”</p>
                  <div className="mt-6 text-sm font-semibold text-slate-900">{t.name}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="faq" className="mx-auto max-w-5xl px-6 py-20 lg:px-8">
          <div className="mb-12 text-center">
            <div className="mb-4 text-sm font-semibold uppercase tracking-[0.2em] text-emerald-600">FAQ</div>
            <h2 className="text-3xl font-bold tracking-tight text-slate-900">Everything you need to know</h2>
          </div>
          <div className="space-y-4">
            {faqs.map((faq) => (
              <details key={faq.q} className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-sm" open={faq.q === 'Can I plan a rooftop without prior gardening experience?'}>
                <summary className="cursor-pointer list-none text-lg font-semibold text-slate-900">{faq.q}</summary>
                <p className="mt-3 text-base leading-7 text-slate-600">{faq.a}</p>
              </details>
            ))}
          </div>
        </section>

        <section className="bg-slate-900 py-20">
          <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-8 px-6 text-center text-white lg:flex-row lg:text-left lg:px-8">
            <div>
              <div className="mb-3 text-sm font-semibold uppercase tracking-[0.2em] text-emerald-300">Start growing</div>
              <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">Build a rooftop garden that works for your life.</h2>
            </div>
            <Link to="/signup" className="inline-flex items-center rounded-full bg-emerald-500 px-6 py-3 font-semibold text-white shadow-lg shadow-emerald-500/30 transition hover:bg-emerald-400">
              Create your plan <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto grid max-w-7xl gap-12 px-6 py-12 text-slate-600 md:grid-cols-4 lg:px-8">
          <div>
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-500 to-green-700">
                <Leaf className="h-5 w-5 text-white" />
              </div>
              <div>
                <div className="font-semibold text-slate-900">RoofTop AI</div>
                <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500">smart gardening</div>
              </div>
            </div>
            <p className="mt-4 text-sm leading-6">AI-powered rooftop gardening for healthier, smarter urban growing relationships.</p>
          </div>
          <div>
            <h3 className="font-semibold text-slate-900">Platform</h3>
            <ul className="mt-4 space-y-2 text-sm">
              <li>Planner</li>
              <li>Plant doctor</li>
              <li>Marketplace</li>
            </ul>
          </div>
          <div>
            <h3 className="font-semibold text-slate-900">Resources</h3>
            <ul className="mt-4 space-y-2 text-sm">
              <li>Knowledge hub</li>
              <li>Guides</li>
              <li>Community</li>
            </ul>
          </div>
          <div>
            <h3 className="font-semibold text-slate-900">Company</h3>
            <ul className="mt-4 space-y-2 text-sm">
              <li>About</li>
              <li>Careers</li>
              <li>Contact</li>
            </ul>
          </div>
        </div>
      </footer>
    </div>
  )
}

function AuthPage({ mode }) {
  const navigate = useNavigate()
  const { signup, login } = useAppStore()
  const schema = mode === 'signup' ? signupSchema : loginSchema

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues: { name: '', email: '', password: '' },
  })

  const onSubmit = (values) => {
    if (mode === 'signup') {
      signup(values)
      toast.success('Welcome to RoofTop AI!')
      navigate('/onboarding')
    } else {
      login(values)
      toast.success('Signed in successfully')
      navigate('/dashboard')
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-emerald-50 via-white to-lime-50 px-4 py-12">
      <div className="grid w-full max-w-6xl overflow-hidden rounded-[32px] border border-slate-200 bg-white shadow-[0_30px_80px_rgba(15,23,42,0.08)] lg:grid-cols-2">
        <div className="relative hidden overflow-hidden bg-gradient-to-br from-emerald-900 via-emerald-800 to-green-700 p-12 text-white lg:flex lg:flex-col lg:justify-between">
          <div>
            <div className="mb-10 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/10 backdrop-blur-sm">
                <Leaf className="h-5 w-5 text-emerald-200" />
              </div>
              <span className="text-lg font-semibold">RoofTop AI</span>
            </div>
            <h2 className="max-w-sm text-4xl font-bold leading-tight">Build a greener rooftop with intelligent guidance.</h2>
          </div>
          <div className="rounded-[28px] border border-white/10 bg-white/5 p-6 backdrop-blur-sm">
            <div className="mb-3 flex items-center justify-between text-sm text-emerald-100">
              <span>Garden health score</span>
              <span>92%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-white/15">
              <div className="h-full w-[92%] rounded-full bg-emerald-300" />
            </div>
            <div className="mt-6 text-sm text-emerald-50/80">Your rooftop is ready for a productive seasonal plan with low-maintenance edible plants and shade-friendly herbs.</div>
          </div>
        </div>

        <div className="flex items-center justify-center p-6 sm:p-10">
          <div className="w-full max-w-md">
            <div className="mb-8 text-center">
              <div className="text-sm font-semibold uppercase tracking-[0.2em] text-emerald-600">{mode === 'signup' ? 'Create account' : 'Welcome back'}</div>
              <h1 className="mt-3 text-3xl font-bold text-slate-900">{mode === 'signup' ? 'Start your rooftop journey' : 'Sign in to your dashboard'}</h1>
            </div>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
              {mode === 'signup' && (
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Full name</label>
                  <input {...register('name')} className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 outline-none transition focus:border-emerald-400 focus:bg-white" placeholder="Aisha Patel" />
                  {errors.name && <p className="mt-1 text-sm text-red-500">{errors.name.message}</p>}
                </div>
              )}

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Email</label>
                <input {...register('email')} className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 outline-none transition focus:border-emerald-400 focus:bg-white" placeholder="you@example.com" />
                {errors.email && <p className="mt-1 text-sm text-red-500">{errors.email.message}</p>}
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Password</label>
                <input type="password" {...register('password')} className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 outline-none transition focus:border-emerald-400 focus:bg-white" placeholder="••••••••" />
                {errors.password && <p className="mt-1 text-sm text-red-500">{errors.password.message}</p>}
              </div>

              <button type="submit" className="w-full rounded-2xl bg-emerald-600 px-4 py-3.5 text-base font-semibold text-white shadow-lg shadow-emerald-600/20 transition hover:bg-emerald-700">
                {mode === 'signup' ? 'Create account' : 'Sign in'}
              </button>
            </form>

            <div className="mt-6 text-center text-sm text-slate-600">
              {mode === 'signup' ? 'Already have an account?' : 'Need an account?'}{' '}
              <Link to={mode === 'signup' ? '/login' : '/signup'} className="font-semibold text-emerald-700">{mode === 'signup' ? 'Log in' : 'Sign up'}</Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function OnboardingPage() {
  const navigate = useNavigate()
  const { saveProfile } = useAppStore()
  const { register, handleSubmit, watch } = useForm({
    defaultValues: {
      name: 'Aisha Patel',
      location: 'Austin, TX',
      rooftopSize: '420',
      rooftopType: 'Terrace garden',
      sunlight: 'Full sun',
      water: 'Municipal supply',
      experience: 'Beginner',
      goals: 'Grow herbs and vegetables',
      budget: '$1,200',
      style: 'Modern edible garden',
      categories: 'Edible greens',
    },
  })

  const currentStep = Number(watch('step') || 1)

  const steps = [
    { title: 'Profile', fields: ['name', 'location', 'experience'] },
    { title: 'Rooftop', fields: ['rooftopSize', 'rooftopType', 'sunlight', 'water'] },
    { title: 'Goals', fields: ['goals', 'budget', 'style', 'categories'] },
  ]

  const onSubmit = (values) => {
    saveProfile(values)
    toast.success('Onboarding complete! Your plan is ready.')
    navigate('/planner')
  }

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-12">
      <div className="mx-auto max-w-5xl rounded-[32px] border border-slate-200 bg-white p-6 shadow-[0_30px_80px_rgba(15,23,42,0.06)] sm:p-8">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <div className="text-sm font-semibold uppercase tracking-[0.2em] text-emerald-600">Onboarding</div>
            <h1 className="mt-2 text-3xl font-bold text-slate-900">Set up your rooftop garden</h1>
          </div>
          <Link to="/dashboard" className="inline-flex items-center gap-2 rounded-full border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700">
            Skip for now <ChevronRight className="h-4 w-4" />
          </Link>
        </div>

        <div className="mb-8 flex gap-3">
          {steps.map((item, index) => (
            <div key={item.title} className={`flex-1 rounded-full border px-3 py-2 text-center text-sm font-medium ${currentStep === index + 1 ? 'border-emerald-500 bg-emerald-50 text-emerald-700' : 'border-slate-200 text-slate-500'}`}>
              {index + 1}. {item.title}
            </div>
          ))}
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          <div className="grid gap-5 md:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">Your name</label>
              <input {...register('name')} className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">Location</label>
              <input {...register('location')} className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">Rooftop size</label>
              <input {...register('rooftopSize')} className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">Rooftop type</label>
              <select {...register('rooftopType')} className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                <option>Terrace garden</option>
                <option>Container garden</option>
                <option>Vertical garden</option>
                <option>Open rooftop</option>
                <option>Covered rooftop</option>
              </select>
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">Sunlight exposure</label>
              <select {...register('sunlight')} className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                <option>Full sun</option>
                <option>Partial sun</option>
                <option>Shade</option>
              </select>
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">Water availability</label>
              <select {...register('water')} className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                <option>Municipal supply</option>
                <option>Rainwater capture</option>
                <option>Limited supply</option>
              </select>
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">Gardening experience</label>
              <select {...register('experience')} className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                <option>Beginner</option>
                <option>Intermediate</option>
                <option>Advanced</option>
              </select>
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">Budget</label>
              <select {...register('budget')} className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                <option>$1,200</option>
                <option>$2,500</option>
                <option>$5,000</option>
              </select>
            </div>
            <div className="md:col-span-2">
              <label className="mb-2 block text-sm font-medium text-slate-700">Gardening goals</label>
              <input {...register('goals')} className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">Preferred style</label>
              <select {...register('style')} className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                <option>Modern edible garden</option>
                <option>Flower-forward oasis</option>
                <option>Minimal sustainable design</option>
              </select>
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">Plant categories</label>
              <select {...register('categories')} className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                <option>Edible greens</option>
                <option>Herbs and pollinators</option>
                <option>Ornamental flowering beds</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <button type="button" className="rounded-full border border-slate-200 px-5 py-2.5 font-medium text-slate-700">Save draft</button>
            <button type="submit" className="rounded-full bg-emerald-600 px-5 py-2.5 font-semibold text-white shadow-lg shadow-emerald-600/20">Continue to planner</button>
          </div>
        </form>
      </div>
    </div>
  )
}

function PlannerPage() {
  const navigate = useNavigate()
  const { savePlan } = useAppStore()
  const { register, handleSubmit } = useForm({
    defaultValues: {
      rooftopSize: '420',
      rooftopType: 'Terrace garden',
      shape: 'Rectangle',
      orientation: 'South facing',
      sunlight: 'Full sun',
      waterSource: 'Municipal supply',
      weightCapacity: '220 kg/m²',
      budget: '$1,500',
      style: 'Modern edible garden',
      purpose: 'Fresh herbs and vegetables',
    },
  })

  const [plan, setPlan] = useState(() => generatePlan({
    rooftopSize: '420',
    rooftopType: 'Terrace garden',
    shape: 'Rectangle',
    orientation: 'South facing',
    sunlight: 'Full sun',
    waterSource: 'Municipal supply',
    weightCapacity: '220 kg/m²',
    budget: '$1,500',
    style: 'Modern edible garden',
    purpose: 'Fresh herbs and vegetables',
  }))

  const onSubmit = (values) => {
    const nextPlan = generatePlan(values)
    setPlan(nextPlan)
    savePlan(nextPlan)
    toast.success('Your rooftop plan has been generated.')
  }

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-12">
      <div className="mx-auto max-w-7xl rounded-[32px] border border-slate-200 bg-white p-6 shadow-[0_30px_80px_rgba(15,23,42,0.06)] sm:p-8">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <div className="text-sm font-semibold uppercase tracking-[0.2em] text-emerald-600">AI Rooftop Planner</div>
            <h1 className="mt-2 text-3xl font-bold text-slate-900">Design a personalized rooftop layout</h1>
          </div>
          <button onClick={() => navigate('/dashboard')} className="rounded-full border border-slate-200 px-4 py-2 font-medium text-slate-700">View dashboard</button>
        </div>

        <div className="grid gap-8 xl:grid-cols-[0.9fr_1.1fr]">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5 rounded-[28px] border border-slate-200 bg-slate-50 p-5">
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">Rooftop dimensions</label>
              <input {...register('rooftopSize')} className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3" />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">Rooftop type</label>
              <select {...register('rooftopType')} className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3">
                <option>Open rooftop</option>
                <option>Partially shaded rooftop</option>
                <option>Fully shaded rooftop</option>
                <option>Covered rooftop</option>
                <option>Small rooftop</option>
                <option>Large rooftop</option>
                <option>Terrace garden</option>
                <option>Container garden</option>
                <option>Vertical garden</option>
              </select>
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">Rooftop shape</label>
              <select {...register('shape')} className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3">
                <option>Rectangle</option>
                <option>Square</option>
                <option>L-shaped</option>
                <option>U-shaped</option>
                <option>Irregular</option>
              </select>
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">Orientation</label>
              <select {...register('orientation')} className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3">
                <option>South facing</option>
                <option>West facing</option>
                <option>East facing</option>
                <option>North facing</option>
              </select>
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">Sunlight exposure</label>
              <select {...register('sunlight')} className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3">
                <option>Full sun</option>
                <option>Partial sun</option>
                <option>Shade</option>
              </select>
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">Water source</label>
              <input {...register('waterSource')} className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3" />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">Weight capacity</label>
              <input {...register('weightCapacity')} className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3" />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">Available budget</label>
              <input {...register('budget')} className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3" />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">Garden style</label>
              <input {...register('style')} className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3" />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">Gardening purpose</label>
              <input {...register('purpose')} className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3" />
            </div>

            <button type="submit" className="w-full rounded-2xl bg-emerald-600 px-4 py-3.5 font-semibold text-white shadow-lg shadow-emerald-600/20 transition hover:bg-emerald-700">
              Generate plan
            </button>
          </form>

          <div className="space-y-6">
            <div className="rounded-[28px] border border-slate-200 bg-gradient-to-br from-emerald-50 to-white p-6">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <div className="text-sm font-semibold uppercase tracking-[0.2em] text-emerald-600">Planner output</div>
                  <h2 className="mt-2 text-2xl font-bold text-slate-900">Recommended rooftop layout</h2>
                </div>
                <div className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-emerald-700">Ready</div>
              </div>
              <p className="text-base leading-7 text-slate-700">{plan.layout}</p>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
              <div className="rounded-[28px] border border-slate-200 bg-white p-5">
                <h3 className="mb-4 text-lg font-semibold text-slate-900">Suitable plant categories</h3>
                <ul className="space-y-2 text-sm text-slate-600">
                  {plan.categories.map((category) => (
                    <li key={category} className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-600" />{category}</li>
                  ))}
                </ul>
              </div>

              <div className="rounded-[28px] border border-slate-200 bg-white p-5">
                <h3 className="mb-4 text-lg font-semibold text-slate-900">Container placements</h3>
                <ul className="space-y-2 text-sm text-slate-600">
                  {plan.containers.map((container) => (
                    <li key={container} className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-600" />{container}</li>
                  ))}
                </ul>
              </div>

              <div className="rounded-[28px] border border-slate-200 bg-white p-5 md:col-span-2">
                <h3 className="mb-4 text-lg font-semibold text-slate-900">Sunlight-based and shade-based arrangement</h3>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="rounded-2xl bg-amber-50 p-4">
                    <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-amber-700"><SunMedium className="h-4 w-4" /> Sun lovers</div>
                    <p className="text-sm text-slate-700">{plan.sunlightZones}</p>
                  </div>
                  <div className="rounded-2xl bg-sky-50 p-4">
                    <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-sky-700"><CloudSun className="h-4 w-4" /> Shade-friendly</div>
                    <p className="text-sm text-slate-700">{plan.shadeZones}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function DashboardPage() {
  const { user, logout } = useAppStore()
  const navigate = useNavigate()

  const { data: summaryCards = [] } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: async () => dashboardCards,
  })

  const tasks = [
    { title: 'Set up drip lines', status: 'Due today', tone: 'bg-emerald-100 text-emerald-700' },
    { title: 'Inspect basil growth', status: 'In review', tone: 'bg-amber-100 text-amber-700' },
    { title: 'Fertilize lettuce bed', status: 'Scheduled', tone: 'bg-sky-100 text-sky-700' },
  ]

  return (
    <div className="min-h-screen bg-slate-100">
      <div className="mx-auto flex max-w-7xl gap-6 px-4 py-6">
        <aside className="hidden w-72 shrink-0 rounded-[28px] border border-slate-200 bg-slate-900 p-5 text-white lg:block">
          <div className="flex items-center gap-3 border-b border-slate-700 pb-6">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-500/20 text-emerald-300"><Leaf className="h-5 w-5" /></div>
            <div>
              <div className="font-semibold">RoofTop AI</div>
              <div className="text-xs text-slate-400">Garden dashboard</div>
            </div>
          </div>

          <nav className="mt-6 space-y-2">
            {[
              ['Overview', Home],
              ['Planner', Trees],
              ['Garden health', Gauge],
              ['Marketplace', ShoppingBag],
              ['Knowledge', BookOpen],
              ['Settings', Settings],
            ].map(([label, Icon]) => (
              <button key={label} className="flex w-full items-center gap-3 rounded-2xl px-3 py-2.5 text-sm font-medium text-slate-200 transition hover:bg-slate-800">
                <Icon className="h-4 w-4" /> {label}
              </button>
            ))}
          </nav>

          <div className="mt-8 rounded-[24px] border border-slate-700 bg-slate-800/60 p-4">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-sm text-slate-300">AI assistant</span>
              <span className="rounded-full bg-emerald-500/20 px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-emerald-300">online</span>
            </div>
            <p className="text-sm leading-6 text-slate-300">Today’s tip: rotate containers for balanced sunlight and stronger root health.</p>
          </div>
        </aside>

        <main className="flex-1">
          <header className="mb-6 rounded-[28px] border border-slate-200 bg-white px-5 py-4 shadow-sm">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-3">
                <button className="lg:hidden"><Menu className="h-5 w-5 text-slate-600" /></button>
                <div>
                  <div className="text-sm font-medium text-slate-500">Good afternoon</div>
                  <h1 className="text-2xl font-bold text-slate-900">{user?.name || 'Aisha'}'s greenhouse</h1>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <button className="rounded-full border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700"><Search className="mr-2 inline h-4 w-4" /> Search</button>
                <button className="rounded-full border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700"><Bell className="h-4 w-4" /></button>
                <button onClick={() => { logout(); navigate('/login'); }} className="rounded-full border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-700"><LogOut className="mr-2 inline h-4 w-4" /> Sign out</button>
              </div>
            </div>
          </header>

          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {summaryCards.map(({ label, value, icon: Icon }) => (
              <div key={label} className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-sm">
                <div className="mb-5 flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-500">{label}</span>
                  <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-700"><Icon className="h-5 w-5" /></div>
                </div>
                <div className="text-3xl font-bold text-slate-900">{value}</div>
              </div>
            ))}
          </section>

          <section className="mt-6 grid gap-6 xl:grid-cols-[1.3fr_0.7fr]">
            <div className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-sm">
              <div className="mb-5 flex items-center justify-between">
                <h2 className="text-xl font-bold text-slate-900">Garden growth</h2>
                <button className="text-sm font-medium text-emerald-700">This season</button>
              </div>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={healthData}>
                    <defs>
                      <linearGradient id="yieldFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#10b981" stopOpacity={0.35} />
                        <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="4 4" stroke="#e2e8f0" />
                    <XAxis dataKey="month" tickLine={false} axisLine={false} />
                    <YAxis tickLine={false} axisLine={false} />
                    <Tooltip />
                    <Area type="monotone" dataKey="yield" stroke="#10b981" strokeWidth={3} fill="url(#yieldFill)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="mb-5 text-xl font-bold text-slate-900">Crop mix</h2>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={productivityData} layout="vertical" margin={{ left: 10 }}>
                    <CartesianGrid strokeDasharray="4 4" stroke="#e2e8f0" />
                    <XAxis type="number" hide />
                    <YAxis dataKey="name" type="category" tickLine={false} axisLine={false} width={70} />
                    <Tooltip />
                    <Bar dataKey="value" radius={[0, 6, 6, 0]} fill="#16a34a" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </section>

          <section className="mt-6 grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
            <div className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-sm">
              <div className="mb-5 flex items-center justify-between">
                <h2 className="text-xl font-bold text-slate-900">Today’s tasks</h2>
                <button className="rounded-full bg-emerald-100 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.2em] text-emerald-700">3 active</button>
              </div>
              <div className="space-y-3">
                {tasks.map((task) => (
                  <div key={task.title} className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <div>
                      <div className="font-medium text-slate-800">{task.title}</div>
                      <div className="mt-1 text-sm text-slate-500">{task.status}</div>
                    </div>
                    <span className={`rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] ${task.tone}`}>{task.status}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-sm">
              <div className="mb-5 flex items-center justify-between">
                <h2 className="text-xl font-bold text-slate-900">Quick insights</h2>
                <Sprout className="h-5 w-5 text-emerald-600" />
              </div>
              <div className="space-y-4">
                <div className="rounded-2xl bg-emerald-50 p-4">
                  <div className="text-sm font-medium text-emerald-700">Water cycle</div>
                  <div className="mt-1 text-base font-semibold text-slate-900">Drip line is 18% more efficient than weekly watering</div>
                </div>
                <div className="rounded-2xl bg-amber-50 p-4">
                  <div className="text-sm font-medium text-amber-700">Nutrition</div>
                  <div className="mt-1 text-base font-semibold text-slate-900">Tomato beds could use a light calcium boost this week</div>
                </div>
                <div className="rounded-2xl bg-sky-50 p-4">
                  <div className="text-sm font-medium text-sky-700">Next best action</div>
                  <div className="mt-1 text-base font-semibold text-slate-900">Add a north-side trellis for climbers and shade herbs</div>
                </div>
              </div>
            </div>
          </section>
        </main>
      </div>
    </div>
  )
}

function generatePlan(values) {
  const size = Number(values.rooftopSize) || 420
  const isSunny = values.sunlight?.toLowerCase().includes('full') || values.sunlight?.toLowerCase().includes('sun')
  const isShade = values.sunlight?.toLowerCase().includes('shade')

  const categories = isShade
    ? ['Shade-tolerant greens', 'Herbs', 'Leaf lettuce', 'Caladiums']
    : isSunny
      ? ['Tomatoes', 'Peppers', 'Cucumbers', 'Pollinator flowers']
      : ['Herbs', 'Leaf greens', 'Bush beans', 'Marigolds']

  const containers = [
    `North edge: ${size > 500 ? 'three elevated herb troughs' : 'two compact herb planters'}`,
    'South border: 6-8 fruiting plants in deep containers',
    'Vertical trellis: climbing beans and sweet peas',
  ]

  return {
    layout: `${values.style || 'Modern edible garden'} plan for a ${values.rooftopType || 'terrace'} rooftop with ${values.orientation || 'south-facing'} exposure. The layout allocates ${Math.max(40, Math.round(size * 0.45))} sq ft for productive beds, ${Math.max(20, Math.round(size * 0.2))} sq ft for herbs, and a compact vertical zone for climbing crops.`,
    categories,
    containers,
    sunlightZones: isSunny ? 'Place fruiting crops in the brightest south and west zones for maximum yield.' : 'Keep leafy greens near the brightest edge and use filtered light for tender herbs.',
    shadeZones: isShade ? 'Use cooler masses such as mint, lettuce, and spinach in the shaded corners and at the north edge.' : 'Reserve the structurally cooler area for herbs, greens, and low-water plantings.',
  }
}

export default App
