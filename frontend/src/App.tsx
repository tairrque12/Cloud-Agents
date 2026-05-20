import { useState, useEffect } from 'react'
import LandingPage from './components/LandingPage'
import ChatWindow from './components/ChatWindow'
import EstimateCard from './components/EstimateCard'
import AdminDashboard from './components/AdminDashboard'

export type Screen = 'landing' | 'chat' | 'estimate' | 'admin'

export interface Estimate {
  priceMin: number
  priceMax: number
  estimatedDate: string
  availableDates: string[]
  intakeId: string
  preferredTiming: string
  summary: string
}

const ADMIN_PATH = '/admin-inkbook-m1g'
/** Client booking — use this URL in artist bio links (e.g. Miguel's Instagram) */
const BOOK_PATH = '/book'
function normalizePath(path: string): string {
  const base = path.split('?')[0].split('#')[0]
  if (base.length > 1 && base.endsWith('/')) return base.slice(0, -1)
  return base || '/'
}

function isClientBookingPath(path = window.location.pathname): boolean {
  const p = normalizePath(path)
  return p === BOOK_PATH || p === '/miguel'
}

function screenFromPath(path = window.location.pathname): Screen {
  const p = normalizePath(path)
  if (p === ADMIN_PATH) return 'admin'
  if (isClientBookingPath(p)) return 'chat'
  return 'landing'
}

function App() {
  const [screen, setScreen] = useState<Screen>(() => screenFromPath())
  const [estimate, setEstimate] = useState<Estimate | null>(null)

  // Re-sync when user navigates with back/forward
  useEffect(() => {
    const onPopState = () => setScreen(screenFromPath())
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  const openClientBooking = () => {
    window.history.replaceState(null, '', BOOK_PATH)
    setScreen('chat')
  }

  const resetAfterEstimate = () => {
    setScreen(isClientBookingPath() ? 'chat' : 'landing')
  }

  return (
    <>
      {screen === 'landing' && (
        <LandingPage onStart={openClientBooking} />
      )}
      {screen === 'chat' && (
        <ChatWindow
          onComplete={(est) => {
            setEstimate(est)
            setScreen('estimate')
          }}
        />
      )}
      {screen === 'estimate' && estimate && (
        <EstimateCard
          estimate={estimate}
          onReset={resetAfterEstimate}
        />
      )}
      {screen === 'admin' && (
        <AdminDashboard />
      )}
    </>
  )
}

export default App
