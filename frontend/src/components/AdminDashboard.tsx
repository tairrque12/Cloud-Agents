// src/components/AdminDashboard.tsx
// Inkbook — Miguel's Admin Dashboard
//
// Access: /admin-inkbook-m1g (secret URL, not linked in public UI)
// Auth: simple password gate — password stored in localStorage on success
// Shows: all pending intakes pulled from backend, with approve/decline actions
//
// This is Miguel's command center when he's not on Telegram.
// Designed to be installable as a PWA shortcut on his home screen.

import { useState, useEffect } from 'react'
import { artistApiPath } from '../config'

const ADMIN_PASSWORD = import.meta.env.VITE_ADMIN_PASSWORD || 'inkbook2024'
const STORAGE_KEY = 'inkbook_admin_auth'

interface Props {
  artistSlug?: string
  adminSecret?: string
}

interface Intake {
  intake_id: string
  client_name: string
  client_contact: string
  placement: string
  coverage: string
  selected_date: string | null
  status: string
  price_min: number
  price_max: number
  session_type: string
  classification: string
  client_message: string
  session_summary: string
  image_count: number
}

// ─── STATUS BADGE ─────────────────────────────────────────────────
function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending:   'rgba(201,168,76,0.15)',
    approved:  'rgba(76,207,130,0.15)',
    declined:  'rgba(207,76,76,0.15)',
    adjusting: 'rgba(76,130,207,0.15)',
  }
  const text: Record<string, string> = {
    pending:   '#C9A84C',
    approved:  '#4CCF82',
    declined:  '#CF4C4C',
    adjusting: '#4C82CF',
  }
  return (
    <span style={{
      padding: '3px 10px',
      borderRadius: '999px',
      fontSize: '10px',
      letterSpacing: '0.1em',
      textTransform: 'uppercase',
      fontWeight: 600,
      background: colors[status] ?? 'rgba(255,255,255,0.05)',
      color: text[status] ?? '#888',
    }}>
      {status}
    </span>
  )
}

// ─── CLASSIFICATION ICON ──────────────────────────────────────────
function ClassIcon({ classification }: { classification: string }) {
  if (classification?.toUpperCase().includes('STRONG')) return <span>🟢</span>
  return <span>🟡</span>
}

// ─── INTAKE CARD ──────────────────────────────────────────────────
function IntakeCard({
  intake,
  artistSlug,
  onAction,
}: {
  intake: Intake
  artistSlug: string
  onAction: () => void
}) {
  const [expanded, setExpanded] = useState(false)
  const [acting, setActing] = useState(false)

  const handleDecision = async (decision: string) => {
    if (acting) return
    setActing(true)
    try {
      await fetch(artistApiPath(artistSlug, 'approve'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ intake_id: intake.intake_id, decision }),
      })
      onAction()
    } catch {
      // non-fatal
    } finally {
      setActing(false)
    }
  }

  return (
    <div style={{
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: '4px',
      overflow: 'hidden',
      marginBottom: '12px',
      position: 'relative',
    }}>
      {/* Corner accents */}
      <div style={{ position: 'absolute', top: 0, left: 0, width: '20px', height: '20px', borderTop: '1px solid var(--gold)', borderLeft: '1px solid var(--gold)' }} />
      <div style={{ position: 'absolute', bottom: 0, right: 0, width: '20px', height: '20px', borderBottom: '1px solid var(--gold)', borderRight: '1px solid var(--gold)' }} />

      {/* Header row */}
      <div
        onClick={() => setExpanded(!expanded)}
        style={{
          padding: '16px 20px',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
        }}
      >
        <ClassIcon classification={intake.classification} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span style={{ fontSize: '15px', fontWeight: 500 }}>{intake.client_name}</span>
            <StatusBadge status={intake.status} />
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 300 }}>
            {intake.placement}
            {intake.coverage && intake.coverage !== 'not specified'
              ? ` — ${intake.coverage}` : ''}
            {' · '}
            <span style={{ color: 'var(--gold)' }}>${intake.price_min}–${intake.price_max}</span>
          </div>
        </div>
        <div style={{ fontSize: '12px', color: 'var(--text-muted)', flexShrink: 0 }}>
          {expanded ? '▲' : '▼'}
        </div>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div style={{ padding: '0 20px 20px', borderTop: '1px solid var(--border)' }}>

          {/* Key details */}
          <div style={{
            display: 'grid', gridTemplateColumns: '1fr 1fr',
            gap: '12px', margin: '16px 0',
          }}>
            <Detail label="Contact" value={
              <a href={`tel:${intake.client_contact}`} style={{ color: 'var(--gold)', textDecoration: 'none' }}>
                {intake.client_contact}
              </a>
            } />
            <Detail label="Selected Date" value={intake.selected_date ?? 'Not selected'} />
            <Detail label="Session Type" value={intake.session_type?.replace('_', ' ')} />
            <Detail label="Images" value={intake.image_count > 0 ? `${intake.image_count} uploaded` : 'None'} />
          </div>

          {/* Client message */}
          {intake.client_message && (
            <div style={{ marginBottom: '14px' }}>
              <p style={{
                fontSize: '10px', color: 'var(--gold)', letterSpacing: '0.15em',
                textTransform: 'uppercase', marginBottom: '8px',
              }}>Drafted Response</p>
              <p style={{
                fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.7,
                fontWeight: 300, background: 'rgba(255,255,255,0.02)',
                padding: '12px', borderRadius: '4px',
                border: '1px solid var(--border)',
              }}>
                {intake.client_message}
              </p>
            </div>
          )}

          {/* Session summary */}
          {intake.session_summary && (
            <div style={{ marginBottom: '16px' }}>
              <p style={{
                fontSize: '10px', color: 'var(--gold)', letterSpacing: '0.15em',
                textTransform: 'uppercase', marginBottom: '8px',
              }}>Session Summary</p>
              <p style={{
                fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.7,
                fontWeight: 300,
              }}>
                {intake.session_summary}
              </p>
            </div>
          )}

          {/* Action buttons — only show for pending */}
          {intake.status === 'pending' && (
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                onClick={() => handleDecision('approved')}
                disabled={acting}
                style={{
                  flex: 1, padding: '12px',
                  background: 'var(--gold)', color: 'var(--black)',
                  border: 'none', borderRadius: '4px',
                  fontSize: '12px', fontWeight: 700,
                  letterSpacing: '0.1em', textTransform: 'uppercase',
                  cursor: acting ? 'default' : 'pointer',
                  opacity: acting ? 0.6 : 1,
                }}
              >
                ✅ Approve
              </button>
              <button
                onClick={() => handleDecision('declined')}
                disabled={acting}
                style={{
                  flex: 1, padding: '12px',
                  background: 'none',
                  color: 'var(--text-muted)',
                  border: '1px solid var(--border)',
                  borderRadius: '4px',
                  fontSize: '12px', fontWeight: 500,
                  letterSpacing: '0.1em', textTransform: 'uppercase',
                  cursor: acting ? 'default' : 'pointer',
                  opacity: acting ? 0.6 : 1,
                }}
              >
                ❌ Decline
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function Detail({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <p style={{
        fontSize: '10px', color: 'var(--text-muted)',
        letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: '3px',
      }}>{label}</p>
      <p style={{ fontSize: '13px', fontWeight: 300 }}>{value}</p>
    </div>
  )
}

// ─── PASSWORD GATE ────────────────────────────────────────────────
function PasswordGate({ onUnlock }: { onUnlock: () => void }) {
  const [input, setInput] = useState('')
  const [error, setError] = useState(false)

  const handleSubmit = () => {
    if (input === ADMIN_PASSWORD) {
      localStorage.setItem(STORAGE_KEY, 'true')
      onUnlock()
    } else {
      setError(true)
      setInput('')
      setTimeout(() => setError(false), 2000)
    }
  }

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      padding: '40px 24px', background: 'var(--black)',
    }}>
      <div style={{
        width: '36px', height: '36px', borderRadius: '50% 50% 50% 0',
        background: 'var(--gold)', transform: 'rotate(-45deg)',
        marginBottom: '32px',
      }} />

      <h1 style={{
        fontFamily: 'var(--font-display)', fontSize: '32px',
        fontWeight: 300, marginBottom: '8px',
      }}>Inkbook</h1>

      <p style={{
        color: 'var(--gold)', fontSize: '11px',
        letterSpacing: '0.2em', textTransform: 'uppercase',
        marginBottom: '48px',
      }}>Artist Dashboard</p>

      <div style={{ width: '100%', maxWidth: '320px' }}>
        <input
          type="password"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSubmit()}
          placeholder="Enter password"
          autoFocus
          style={{
            width: '100%', padding: '14px 16px',
            background: 'var(--surface)',
            border: `1px solid ${error ? '#CF4C4C' : 'var(--border)'}`,
            borderRadius: '4px', color: 'var(--text)',
            fontSize: '14px', outline: 'none',
            boxSizing: 'border-box',
            transition: 'border-color 0.15s ease',
            marginBottom: '12px',
          }}
        />
        {error && (
          <p style={{
            color: '#CF4C4C', fontSize: '12px',
            marginBottom: '12px', textAlign: 'center',
          }}>
            Incorrect password
          </p>
        )}
        <button
          onClick={handleSubmit}
          style={{
            width: '100%', padding: '14px',
            background: 'var(--gold)', color: 'var(--black)',
            border: 'none', borderRadius: '4px',
            fontSize: '12px', fontWeight: 700,
            letterSpacing: '0.15em', textTransform: 'uppercase',
            cursor: 'pointer',
          }}
        >
          Enter →
        </button>
      </div>
    </div>
  )
}

// ─── MAIN DASHBOARD ───────────────────────────────────────────────
export default function AdminDashboard({ artistSlug = 'miguel', adminSecret }: Props) {
  const [authed, setAuthed] = useState(() => {
    if (adminSecret) return true
    return localStorage.getItem(STORAGE_KEY) === 'true'
  })
  const [intakes, setIntakes] = useState<Intake[]>([])
  const [artistName, setArtistName] = useState('')
  const [loading, setLoading] = useState(false)
  const [filter, setFilter] = useState<'all' | 'pending' | 'approved' | 'declined'>('pending')

  const fetchIntakes = async () => {
    setLoading(true)
    try {
      const res = await fetch(artistApiPath(artistSlug, 'intakes'))
      const data = await res.json()
      setIntakes(data.intakes ?? [])
      setArtistName(data.artist?.name ?? artistSlug)
    } catch {
      setIntakes([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!authed) return
    const id = setTimeout(fetchIntakes, 0)
    return () => clearTimeout(id)
  }, [authed, artistSlug])

  if (!authed) {
    return <PasswordGate onUnlock={() => setAuthed(true)} />
  }

  const filtered = filter === 'all'
    ? intakes
    : intakes.filter(i => i.status === filter)

  const counts = {
    all: intakes.length,
    pending: intakes.filter(i => i.status === 'pending').length,
    approved: intakes.filter(i => i.status === 'approved').length,
    declined: intakes.filter(i => i.status === 'declined').length,
  }

  return (
    <div style={{
      minHeight: '100vh', background: 'var(--black)',
      maxWidth: '600px', margin: '0 auto',
    }}>
      {/* Header */}
      <div style={{
        padding: '20px 20px 0',
        borderBottom: '1px solid var(--border)',
        position: 'sticky', top: 0,
        background: 'var(--black)', zIndex: 10,
      }}>
        <div style={{
          display: 'flex', alignItems: 'center',
          justifyContent: 'space-between', marginBottom: '16px',
        }}>
          <div>
            <h2 style={{
              fontFamily: 'var(--font-display)', fontSize: '22px',
              fontWeight: 300, marginBottom: '2px',
            }}>Inkbook</h2>
            <p style={{
              color: 'var(--gold)', fontSize: '10px',
              letterSpacing: '0.2em', textTransform: 'uppercase',
            }}>{artistName ? `${artistName}'s Dashboard` : 'Artist Dashboard'}</p>
          </div>
          <button
            onClick={fetchIntakes}
            style={{
              padding: '8px 16px', background: 'none',
              border: '1px solid var(--border)',
              color: 'var(--text-muted)', borderRadius: '4px',
              fontSize: '12px', cursor: 'pointer',
            }}
          >
            Refresh
          </button>
        </div>

        {/* Filter tabs */}
        <div style={{ display: 'flex', gap: '4px', paddingBottom: '0' }}>
          {(['pending', 'all', 'approved', 'declined'] as const).map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              style={{
                padding: '8px 14px',
                background: 'none',
                border: 'none',
                borderBottom: filter === f ? '2px solid var(--gold)' : '2px solid transparent',
                color: filter === f ? 'var(--gold)' : 'var(--text-muted)',
                fontSize: '12px', fontWeight: filter === f ? 600 : 400,
                cursor: 'pointer',
                letterSpacing: '0.05em',
                transition: 'all 0.15s ease',
              }}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
              {' '}
              <span style={{
                fontSize: '10px', opacity: 0.7,
              }}>
                ({counts[f]})
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div style={{ padding: '20px' }}>
        {loading && (
          <div style={{
            textAlign: 'center', padding: '60px 0',
            color: 'var(--text-muted)', fontSize: '13px',
          }}>
            Loading intakes…
          </div>
        )}

        {!loading && filtered.length === 0 && (
          <div style={{
            textAlign: 'center', padding: '60px 0',
          }}>
            <p style={{
              color: 'var(--text-muted)', fontSize: '13px',
              fontWeight: 300, marginBottom: '8px',
            }}>
              {filter === 'pending'
                ? 'No pending requests right now.'
                : `No ${filter} requests.`}
            </p>
            <p style={{ color: 'var(--text-muted)', fontSize: '11px', opacity: 0.5 }}>
              New requests appear here when clients book.
            </p>
          </div>
        )}

        {!loading && filtered.map(intake => (
          <IntakeCard
            key={intake.intake_id}
            intake={intake}
            artistSlug={artistSlug}
            onAction={fetchIntakes}
          />
        ))}
      </div>

      {/* Logout */}
      <div style={{ padding: '0 20px 40px', textAlign: 'center' }}>
        <button
          onClick={() => {
            localStorage.removeItem(STORAGE_KEY)
            setAuthed(false)
          }}
          style={{
            background: 'none', border: 'none',
            color: 'var(--text-muted)', fontSize: '11px',
            cursor: 'pointer', opacity: 0.5,
            letterSpacing: '0.08em',
          }}
        >
          Sign out
        </button>
      </div>
    </div>
  )
}