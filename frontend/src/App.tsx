import { useState } from 'react'
import LandingPage from './components/LandingPage'
import ChatWindow from './components/ChatWindow'
import EstimateCard from './components/EstimateCard'

export type Screen = 'landing' | 'chat' | 'estimate'

export interface Estimate {
  priceMin: number
  priceMax: number
  estimatedDate: string
  summary: string
}

function App() {
  const [screen, setScreen] = useState<Screen>('landing')
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
    </>
  )
}

export default App