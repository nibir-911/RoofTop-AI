import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import './index.css'
import App from './App.jsx'

// Aggressively purge any legacy glove or dummy placeholder data from localStorage
try {
  const GLOVE_PATTERNS = ['1501004318641', '1622383563227', 'glove']
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i)
    if (!key) continue
    const val = localStorage.getItem(key)
    if (val && GLOVE_PATTERNS.some(p => val.toLowerCase().includes(p))) {
      console.warn(`[Cache Purge] Purging legacy glove data from localStorage key: ${key}`)
      try {
        const parsed = JSON.parse(val)
        if (parsed && typeof parsed === 'object') {
          let str = JSON.stringify(parsed)
          GLOVE_PATTERNS.forEach(p => {
            const re = new RegExp(`https?:\\/\\/[^"\'\\s]*${p}[^"\'\\s]*`, 'gi')
            str = str.replace(re, '')
          })
          localStorage.setItem(key, str)
        } else {
          localStorage.removeItem(key)
        }
      } catch {
        localStorage.removeItem(key)
      }
    }
  }
} catch (e) {
  console.warn('LocalStorage glove cleanup notice:', e)
}

const queryClient = new QueryClient()

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <App />
        <Toaster position="top-right" toastOptions={{ duration: 2500 }} />
      </QueryClientProvider>
    </BrowserRouter>
  </StrictMode>,
)
