import { useEffect, useState } from 'react'
import { API_BASE } from '../config'

export interface LandingArtist {
  id: string
  name: string
  slug: string
  city: string | null
  state: string | null
  instagram_handle: string | null
  specialties: string[]
  bio: string | null
}

function listArtistsUrl(): string {
  return `${API_BASE}/api/artists`
}

function instagramUrl(handle: string): string {
  const cleaned = handle.trim().replace(/^@/, '')
  return `https://instagram.com/${cleaned}`
}

function locationLabel(city: string | null, state: string | null): string {
  const parts = [city, state].filter(Boolean)
  return parts.join(', ')
}

export default function LandingPage() {
  const [artists, setArtists] = useState<LandingArtist[]>([])
  const [loading, setLoading] = useState(true)
  const [fetchError, setFetchError] = useState('')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setFetchError('')

    fetch(listArtistsUrl())
      .then(async (res) => {
        if (!res.ok) {
          throw new Error('Could not load artists')
        }
        const data = (await res.json()) as { artists?: LandingArtist[] }
        if (!cancelled) {
          setArtists(data.artists ?? [])
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setFetchError(
            err instanceof Error ? err.message : 'Could not load artists'
          )
          setArtists([])
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div style={{ background: 'var(--black)', minHeight: '100vh', color: 'var(--text)' }}>
      {/* Hero */}
      <section
        style={{
          padding: '96px 24px 72px',
          textAlign: 'center',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            position: 'absolute',
            top: '40%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            width: 560,
            height: 560,
            borderRadius: '50%',
            background:
              'radial-gradient(circle, rgba(201,168,76,0.06) 0%, transparent 65%)',
            pointerEvents: 'none',
          }}
        />
        <p
          style={{
            color: 'var(--gold)',
            letterSpacing: '0.22em',
            fontSize: 11,
            marginBottom: 20,
            position: 'relative',
          }}
        >
          INKBOOK
        </p>
        <h1
          style={{
            fontFamily: 'var(--font-display)',
            fontWeight: 300,
            fontSize: 'clamp(2rem, 5vw, 3.25rem)',
            lineHeight: 1.15,
            maxWidth: 720,
            margin: '0 auto 20px',
            position: 'relative',
          }}
        >
          Your next tattoo starts with a{' '}
          <span style={{ color: 'var(--gold)' }}>conversation.</span>
        </h1>
        <p
          style={{
            color: 'var(--text-muted)',
            fontSize: 'clamp(1rem, 2.5vw, 1.125rem)',
            lineHeight: 1.65,
            maxWidth: 520,
            margin: '0 auto',
            position: 'relative',
          }}
        >
          Browse artists, get an instant quote, and book — all without sliding into
          anyone&apos;s DMs.
        </p>
      </section>

      {/* Artist grid */}
      <section style={{ padding: '0 24px 80px', maxWidth: 1100, margin: '0 auto' }}>
        {loading && (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
              gap: 20,
            }}
          >
            {[0, 1, 2].map((i) => (
              <ArtistCardSkeleton key={i} />
            ))}
          </div>
        )}

        {!loading && fetchError && (
          <p style={{ textAlign: 'center', color: '#e07070', padding: '32px 0' }}>
            {fetchError}
          </p>
        )}

        {!loading && !fetchError && artists.length === 0 && (
          <p
            style={{
              textAlign: 'center',
              color: 'var(--text-muted)',
              fontSize: 18,
              padding: '48px 0',
            }}
          >
            Artists coming soon.
          </p>
        )}

        {!loading && !fetchError && artists.length > 0 && (
          <div className="artist-grid">
            {artists.map((artist) => (
              <ArtistCard key={artist.id} artist={artist} />
            ))}
          </div>
        )}
      </section>

      {/* Artist CTA */}
      <section
        style={{
          padding: '80px 24px 96px',
          textAlign: 'center',
          background: 'var(--surface)',
          borderTop: '1px solid var(--border)',
        }}
      >
        <h2
          style={{
            fontFamily: 'var(--font-display)',
            fontWeight: 400,
            fontSize: 'clamp(1.75rem, 4vw, 2.5rem)',
            marginBottom: 16,
          }}
        >
          Are you a tattoo artist?
        </h2>
        <p
          style={{
            color: 'var(--text-muted)',
            fontSize: 16,
            lineHeight: 1.65,
            maxWidth: 440,
            margin: '0 auto 32px',
          }}
        >
          Get your own AI booking agent. No more DMs. No more back and forth.
        </p>
        <a href="/onboard" style={ctaButtonStyle}>
          Apply for early access
        </a>
      </section>

      <style>{`
        .artist-grid {
          display: grid;
          grid-template-columns: 1fr;
          gap: 20px;
        }
        @media (min-width: 640px) {
          .artist-grid {
            grid-template-columns: repeat(2, 1fr);
          }
        }
        @media (min-width: 960px) {
          .artist-grid {
            grid-template-columns: repeat(3, 1fr);
          }
        }
        .artist-card {
          transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
        }
        .artist-card:hover {
          transform: translateY(-4px);
          border-color: rgba(201, 168, 76, 0.35) !important;
          box-shadow: 0 12px 32px rgba(0, 0, 0, 0.35);
        }
        @keyframes skeleton-pulse {
          0%, 100% { opacity: 0.35; }
          50% { opacity: 0.65; }
        }
        .skeleton-block {
          animation: skeleton-pulse 1.4s ease-in-out infinite;
          background: rgba(201, 168, 76, 0.08);
          border-radius: 4px;
        }
      `}</style>
    </div>
  )
}

function ArtistCard({ artist }: { artist: LandingArtist }) {
  const location = locationLabel(artist.city, artist.state)
  const specialties = artist.specialties?.filter(Boolean) ?? []
  const handle = artist.instagram_handle?.trim()

  return (
    <article
      className="artist-card"
      style={{
        border: '1px solid var(--border)',
        borderRadius: 4,
        padding: 24,
        background: 'var(--surface)',
        display: 'flex',
        flexDirection: 'column',
        gap: 14,
      }}
    >
      <div>
        <h3
          style={{
            fontFamily: 'var(--font-display)',
            fontSize: '1.65rem',
            fontWeight: 400,
            marginBottom: 6,
          }}
        >
          {artist.name}
        </h3>
        {location && (
          <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>{location}</p>
        )}
      </div>

      {artist.bio && (
        <p
          style={{
            color: 'var(--text-muted)',
            fontSize: 14,
            lineHeight: 1.55,
            display: '-webkit-box',
            WebkitLineClamp: 3,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
          {artist.bio}
        </p>
      )}

      {specialties.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {specialties.map((tag) => (
            <span
              key={tag}
              style={{
                fontSize: 11,
                letterSpacing: '0.04em',
                textTransform: 'lowercase',
                padding: '5px 10px',
                border: '1px solid rgba(201, 168, 76, 0.45)',
                borderRadius: 999,
                color: 'var(--gold)',
              }}
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {handle && (
        <a
          href={instagramUrl(handle)}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            color: 'var(--text-muted)',
            fontSize: 13,
            textDecoration: 'none',
          }}
        >
          @{handle.replace(/^@/, '')}
        </a>
      )}

      <a
        href={`/${artist.slug}`}
        style={{
          ...ctaButtonStyle,
          marginTop: 'auto',
          textAlign: 'center',
          display: 'block',
        }}
      >
        Book now
      </a>
    </article>
  )
}

function ArtistCardSkeleton() {
  return (
    <div
      style={{
        border: '1px solid var(--border)',
        borderRadius: 4,
        padding: 24,
        background: 'var(--surface)',
      }}
    >
      <div className="skeleton-block" style={{ height: 28, width: '70%', marginBottom: 12 }} />
      <div className="skeleton-block" style={{ height: 14, width: '45%', marginBottom: 20 }} />
      <div className="skeleton-block" style={{ height: 48, width: '100%', marginBottom: 16 }} />
      <div className="skeleton-block" style={{ height: 44, width: '100%' }} />
    </div>
  )
}

const ctaButtonStyle: import('react').CSSProperties = {
  display: 'inline-block',
  padding: '14px 28px',
  background: 'var(--gold)',
  color: 'var(--black)',
  fontWeight: 500,
  fontSize: 15,
  borderRadius: 2,
  textDecoration: 'none',
}
