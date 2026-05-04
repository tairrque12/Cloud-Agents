import { useState } from 'react'
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

function App() {
  const [screen, setScreen] = useState<Screen>(() => {
    if (window.location.pathname === ADMIN_PATH) return 'admin'
    return 'landing'
  })
  const [estimate, setEstimate] = useState<Estimate | null>(null)

  return (
    <>
      {screen === 'landing' && (
        <LandingPage onStart={() => setScreen('chat')} />
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
          onReset={() => setScreen('landing')}
        />
      )}
      {screen === 'admin' && (
        <AdminDashboard />
      )}
    </>
  )
}

export default App
