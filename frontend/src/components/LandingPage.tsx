// src/components/LandingPage.tsx
// Inkbook — Platform marketing page (founding artist waitlist)

import { useState, type CSSProperties, type FocusEvent } from 'react'

const API_BASE = 'https://inkbook-4tlr.onrender.com'

interface Props {
  onStart: () => void
}

const STATS = [
  { value: '4–7', lines: ['Days of DMs saved', 'per booking'] },
  { value: '90s', lines: ['From inquiry', 'to estimate'] },
  { value: '100%', lines: ['You control', 'every booking'] },
]

export default function LandingPage({ onStart }: Props) {
  const [name, setName] = useState('')
  const [instagram, setInstagram] = useState('')
  const [email, setEmail] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('')
  const [errors, setErrors] = useState({ name: false, instagram: false, email: false })

  const inputBorder = (field: keyof typeof errors) =>
    errors[field]
      ? '1px solid rgba(220,80,80,0.6)'
      : '1px solid rgba(201,168,76,0.15)'

  const inputStyle = (field: keyof typeof errors): CSSProperties => ({
    background: 'rgba(255,255,255,0.03)',
    border: inputBorder(field),
    color: 'var(--text)',
    padding: '14px 18px',
    fontSize: '16px',
    borderRadius: '2px',
    outline: 'none',
    width: '100%',
    boxSizing: 'border-box',
  })

  const focusHandlers = {
    onFocus: (e: FocusEvent<HTMLInputElement>) => {
      if (!e.currentTarget.style.border.includes('220,80,80')) {
        e.currentTarget.style.borderColor = 'rgba(201,168,76,0.45)'
      }
    },
    onBlur: (e: FocusEvent<HTMLInputElement>) => {
      const field = e.currentTarget.dataset.field as keyof typeof errors
      e.currentTarget.style.borderColor = errors[field]
        ? 'rgba(220,80,80,0.6)'
        : 'rgba(201,168,76,0.15)'
    },
  }

  const handleSubmit = async () => {
    const nextErrors = {
      name: !name.trim(),
      instagram: !instagram.trim(),
      email: !email.trim(),
    }
    setErrors(nextErrors)
    setSubmitError('')
    if (nextErrors.name || nextErrors.instagram || nextErrors.email) return

    setSubmitting(true)
    try {
      const res = await fetch(`${API_BASE}/api/beta/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(),
          instagram: instagram.trim(),
          email: email.trim(),
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(
          typeof data.detail === 'string'
            ? data.detail
            : 'Something went wrong. Please try again.'
        )
      }
      setSubmitted(true)
    } catch (err) {
      setSubmitError(
        err instanceof Error ? err.message : 'Something went wrong. Please try again.'
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div
      className="inkbook-landing"
      style={{
        background: 'var(--black)',
        minHeight: '100vh',
        width: '100%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '80px 24px 120px',
        position: 'relative',
        overflow: 'hidden',
        color: 'var(--text)',
        textAlign: 'center',
        boxSizing: 'border-box',
      }}
    >
      <div style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        width: '600px',
        height: '600px',
        borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(201,168,76,0.05) 0%, transparent 65%)',
        pointerEvents: 'none',
      }} />

      <div style={{
        position: 'relative',
        zIndex: 1,
        width: '100%',
        maxWidth: '480px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
      }}>
        {/* Wordmark */}
        <div style={{
          fontSize: '11px',
          letterSpacing: '0.28em',
          textTransform: 'uppercase',
          color: 'var(--gold)',
          opacity: 0.7,
          marginBottom: '80px',
        }}>
          <span style={{
            width: '10px',
            height: '10px',
            borderRadius: '50% 50% 50% 0',
            background: 'var(--gold)',
            transform: 'rotate(-45deg)',
            display: 'inline-block',
            marginRight: '10px',
            verticalAlign: 'middle',
            opacity: 0.7,
          }} />
          Inkbook
        </div>

        {/* Headline */}
        <h1
          className="inkbook-headline"
          style={{
            fontFamily: 'var(--font-display)',
            fontWeight: 300,
            lineHeight: 1.1,
            fontSize: 'clamp(36px, 6vw, 64px)',
            letterSpacing: '-0.02em',
            color: 'var(--text)',
            maxWidth: '680px',
            marginBottom: '28px',
          }}
        >
          Every hour spent on DMs<br />
          is an hour not spent<br />
          <span style={{ color: 'var(--gold)' }}>on the work.</span>
        </h1>

        {/* Body */}
        <p style={{
          fontSize: '16px',
          color: 'var(--text-muted)',
          lineHeight: 1.9,
          fontWeight: 300,
          maxWidth: '400px',
          marginBottom: '64px',
        }}>
          Inkbook handles your client intake — pricing,
          scheduling, and quotes — so the only decision
          left is yours. Review. Approve. Get back to the art.
        </p>

        {/* Form */}
        <div style={{ width: '100%', maxWidth: '360px', marginBottom: submitted ? '48px' : '0' }}>
          {submitted ? (
            <div style={{ marginBottom: '100px' }}>
              <p style={{
                color: 'var(--gold)',
                fontSize: '11px',
                letterSpacing: '0.2em',
                textTransform: 'uppercase',
              }}>
                Application received
              </p>
              <p style={{
                fontSize: '18px',
                fontWeight: 300,
                marginTop: '12px',
                color: 'var(--text-muted)',
                lineHeight: 1.7,
              }}>
                We'll be in touch as we<br />
                onboard founding artists.
              </p>
            </div>
          ) : (
            <>
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '10px',
                marginBottom: '20px',
              }}>
                <input
                  type="text"
                  className="inkbook-input"
                  data-field="name"
                  placeholder="Your name"
                  value={name}
                  disabled={submitting}
                  onChange={e => {
                    setName(e.target.value)
                    if (errors.name) setErrors(prev => ({ ...prev, name: false }))
                  }}
                  style={inputStyle('name')}
                  {...focusHandlers}
                />
                <input
                  type="text"
                  className="inkbook-input"
                  data-field="instagram"
                  placeholder="Instagram handle"
                  value={instagram}
                  disabled={submitting}
                  onChange={e => {
                    setInstagram(e.target.value)
                    if (errors.instagram) setErrors(prev => ({ ...prev, instagram: false }))
                  }}
                  style={inputStyle('instagram')}
                  {...focusHandlers}
                />
                <input
                  type="email"
                  className="inkbook-input"
                  data-field="email"
                  placeholder="Email address"
                  value={email}
                  disabled={submitting}
                  onChange={e => {
                    setEmail(e.target.value)
                    if (errors.email) setErrors(prev => ({ ...prev, email: false }))
                  }}
                  style={inputStyle('email')}
                  {...focusHandlers}
                />
                <button
                  type="button"
                  onClick={handleSubmit}
                  disabled={submitting}
                  style={{
                    background: 'var(--gold)',
                    color: 'var(--black)',
                    fontSize: '11px',
                    letterSpacing: '0.18em',
                    textTransform: 'uppercase',
                    fontWeight: 700,
                    border: 'none',
                    padding: '16px',
                    width: '100%',
                    borderRadius: '2px',
                    marginTop: '4px',
                    cursor: submitting ? 'wait' : 'pointer',
                    opacity: submitting ? 0.7 : 1,
                    transition: 'opacity 0.15s ease',
                  }}
                  onMouseEnter={e => {
                    if (!submitting) e.currentTarget.style.opacity = '0.88'
                  }}
                  onMouseLeave={e => {
                    if (!submitting) e.currentTarget.style.opacity = '1'
                  }}
                >
                  {submitting ? 'Submitting...' : 'Apply for founding access →'}
                </button>
              </div>

              {submitError && (
                <p style={{
                  color: 'rgba(220,80,80,0.85)',
                  fontSize: '12px',
                  marginBottom: '16px',
                  lineHeight: 1.5,
                }}>
                  {submitError}
                </p>
              )}

              <p style={{
                fontSize: '11px',
                color: 'var(--text-muted)',
                letterSpacing: '0.06em',
                opacity: 0.5,
                marginBottom: '100px',
              }}>
                No contracts · No setup fees during beta
              </p>
            </>
          )}
        </div>

        {/* Divider */}
        <div style={{
          width: '1px',
          height: '48px',
          margin: '0 auto 48px',
          background: 'linear-gradient(to bottom, transparent, rgba(201,168,76,0.25), transparent)',
        }} />

        {/* Stats */}
        <div
          className="inkbook-stats"
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            justifyContent: 'center',
            gap: '48px',
            marginBottom: '24px',
            width: '100%',
          }}
        >
          {STATS.map(stat => (
            <div key={stat.value} className="inkbook-stat">
              <p style={{
                fontSize: '28px',
                fontWeight: 300,
                color: 'var(--gold)',
                letterSpacing: '-0.02em',
                marginBottom: '4px',
                fontFamily: 'var(--font-display)',
              }}>
                {stat.value}
              </p>
              {stat.lines.map(line => (
                <p
                  key={line}
                  style={{
                    fontSize: '11px',
                    color: 'var(--text-muted)',
                    letterSpacing: '0.1em',
                    textTransform: 'uppercase',
                    lineHeight: 1.5,
                    opacity: 0.6,
                  }}
                >
                  {line}
                </p>
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* Footer */}
      <footer style={{
        position: 'absolute',
        bottom: '28px',
        left: 0,
        right: 0,
        zIndex: 1,
      }}>
        <p style={{
          fontSize: '10px',
          color: 'var(--text-muted)',
          letterSpacing: '0.12em',
          textTransform: 'uppercase',
          opacity: 0.5,
          marginBottom: '8px',
        }}>
          Inkbook · Built for artists
        </p>
        <span
          onClick={onStart}
          role="button"
          tabIndex={0}
          onKeyDown={e => e.key === 'Enter' && onStart()}
          style={{
            fontSize: '10px',
            color: 'var(--text-muted)',
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
            opacity: 0.25,
            cursor: 'pointer',
          }}
          onMouseEnter={e => (e.currentTarget.style.opacity = '0.5')}
          onMouseLeave={e => (e.currentTarget.style.opacity = '0.25')}
        >
          Already on Inkbook?
        </span>
      </footer>

      <style>{`
        .inkbook-input::placeholder {
          color: rgba(232,229,223,0.22);
        }
        @media (max-width: 480px) {
          .inkbook-landing {
            padding: 60px 20px 100px !important;
          }
          .inkbook-headline {
            font-size: clamp(32px, 8vw, 48px) !important;
          }
          .inkbook-stats {
            gap: 32px !important;
          }
          .inkbook-stat {
            flex: 1 1 80px !important;
          }
        }
      `}</style>
    </div>
  )
}
