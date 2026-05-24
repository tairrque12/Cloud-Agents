import { useState, useEffect } from 'react'
import ChatWindow from './components/ChatWindow'
import EstimateCard from './components/EstimateCard'
import AdminDashboard from './components/AdminDashboard'
import ArtistOnboarding from './components/ArtistOnboarding'
import { MIGUEL_FALLBACK, type ArtistProfile } from './types/artist'
import { artistProfilePath } from './config'

export type Screen = 'chat' | 'estimate' | 'admin' | 'onboard'

export interface Estimate {
  priceMin: number
  priceMax: number
  estimatedDate: string
  availableDates: string[]
  intakeId: string
  preferredTiming: string
  summary: string
}

const LEGACY_ADMIN_PATH = '/admin-inkbook-m1g'
const LEGACY_BOOK_PATH = '/book'
const ONBOARD_PATH = '/onboard'

const RESERVED_SLUGS = new Set([
  'onboard',
  'book',
  'miguel',
  'admin',
  'admin-inkbook-m1g',
  'beta',
  'api',
])

function normalizePath(path: string): string {
  const base = path.split('?')[0].split('#')[0]
  if (base.length > 1 && base.endsWith('/')) return base.slice(0, -1)
  return base || '/'
}

function parseRoute(path = window.location.pathname): {
  screen: Screen
  artistSlug: string
  adminSecret?: string
} {
  const p = normalizePath(path)

  if (p === '/' || p === ONBOARD_PATH) {
    return { screen: 'onboard', artistSlug: 'miguel' }
  }

  if (p === LEGACY_ADMIN_PATH) {
    return { screen: 'admin', artistSlug: 'miguel' }
  }

  const adminMatch = p.match(/^\/admin\/([^/]+)\/([^/]+)$/)
  if (adminMatch) {
    return { screen: 'admin', artistSlug: adminMatch[1], adminSecret: adminMatch[2] }
  }

  const bookMatch = p.match(/^\/book\/([^/]+)$/)
  if (bookMatch) {
    return { screen: 'chat', artistSlug: bookMatch[1] }
  }

  if (p === LEGACY_BOOK_PATH || p === '/miguel') {
    return { screen: 'chat', artistSlug: 'miguel' }
  }

  const slugMatch = p.match(/^\/([^/]+)$/)
  if (slugMatch && !RESERVED_SLUGS.has(slugMatch[1])) {
    return { screen: 'chat', artistSlug: slugMatch[1] }
  }

  return { screen: 'onboard', artistSlug: 'miguel' }
}

function App() {
  const initialRoute = parseRoute()
  const [screen, setScreen] = useState<Screen>(initialRoute.screen)
  const [artistSlug, setArtistSlug] = useState(initialRoute.artistSlug)
  const [adminSecret, setAdminSecret] = useState(initialRoute.adminSecret)
  const [artist, setArtist] = useState<ArtistProfile | null>(null)
  const [artistError, setArtistError] = useState('')
  const [estimate, setEstimate] = useState<Estimate | null>(null)

  useEffect(() => {
    const route = parseRoute()
    if (window.location.pathname === '/' && route.screen === 'onboard') {
      window.history.replaceState(null, '', ONBOARD_PATH)
    }
  }, [])

  useEffect(() => {
    const onPopState = () => {
      const route = parseRoute()
      setScreen(route.screen)
      setArtistSlug(route.artistSlug)
      setAdminSecret(route.adminSecret)
    }
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  useEffect(() => {
    if (screen !== 'chat' && screen !== 'estimate') return

    let cancelled = false
    const isLegacyMiguel = artistSlug === 'miguel'
    setArtistError('')
    if (isLegacyMiguel) {
      setArtist(MIGUEL_FALLBACK)
    } else {
      setArtist(null)
    }

    fetch(artistProfilePath(artistSlug))
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json().catch(() => ({}))
          throw new Error(
            typeof data.detail === 'string' ? data.detail : 'Artist not found'
          )
        }
        return res.json() as Promise<ArtistProfile>
      })
      .then((profile) => {
        if (!cancelled) setArtist(profile)
      })
      .catch((err) => {
        if (!cancelled) {
          if (isLegacyMiguel) {
            setArtist(MIGUEL_FALLBACK)
            setArtistError('')
          } else {
            setArtist(null)
            setArtistError(
              err instanceof Error ? err.message : 'Artist not found'
            )
          }
        }
      })

    return () => {
      cancelled = true
    }
  }, [artistSlug, screen])

  const resetAfterEstimate = () => {
    const route = parseRoute()
    setScreen(route.screen === 'chat' ? 'chat' : 'onboard')
  }

  const notFoundMessage =
    artistSlug === 'miguel' ? artistError : "This page doesn't exist"

  return (
    <>
      {screen === 'onboard' && <ArtistOnboarding />}
      {screen === 'chat' && (
        artistError ? (
          <LoadingState message={notFoundMessage} error />
        ) : (
          <ChatWindow
            artist={artist ?? (artistSlug === 'miguel' ? MIGUEL_FALLBACK : null)}
            artistSlug={artistSlug}
            onComplete={(est) => {
              setEstimate(est)
              setScreen('estimate')
            }}
          />
        )
      )}
      {screen === 'estimate' && estimate && (artist ?? (artistSlug === 'miguel' ? MIGUEL_FALLBACK : null)) && (
        <EstimateCard
          artist={artist ?? MIGUEL_FALLBACK}
          artistSlug={artistSlug}
          estimate={estimate}
          onReset={resetAfterEstimate}
        />
      )}
      {screen === 'admin' && (
        <AdminDashboard artistSlug={artistSlug} adminSecret={adminSecret} />
      )}
    </>
  )
}

function LoadingState({ message, error = false }: { message: string; error?: boolean }) {
  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--black)',
      color: error ? '#e07070' : 'var(--text-muted)',
      padding: 24,
      textAlign: 'center',
    }}>
      {message}
    </div>
  )
}

export default App
