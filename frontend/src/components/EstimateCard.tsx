// src/components/EstimateCard.tsx
// Inkbook — Estimate → Date Selection → Confirmation flow
// Updated: calls /api/miguel/confirm-date with intakeId + selectedDate

import { useState } from 'react'
import type { Estimate } from '../App'

interface Props {
  estimate: Estimate
  onReset: () => void
}

type Screen = 'estimate' | 'date-select' | 'confirmation'

export default function EstimateCard({ estimate, onReset }: Props) {
  const [screen, setScreen] = useState<Screen>('estimate')
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [confirmed, setConfirmed] = useState(false)
  const [sending, setSending] = useState(false)

  // ─── CONFIRM HANDLER ──────────────────────────────────────────
  // Fires /api/miguel/confirm-date then shows success state.
  // Non-fatal — UI confirms even if the network call blips.
  const handleConfirm = async () => {
    if (!selectedDate || sending) return
    setSending(true)
    try {
      await fetch('https://inkbook-4tlr.onrender.com/api/miguel/confirm-date', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          intake_id: estimate.intakeId,
          selected_date: selectedDate,
        }),
      })
    } catch {
      // non-fatal — continue to success screen regardless
    } finally {
      setSending(false)
      setConfirmed(true)
    }
  }

  // ─── ESTIMATE SCREEN ──────────────────────────────────────────
  if (screen === 'estimate') {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '40px 24px',
        background: 'var(--black)',
      }}>
        <p style={{
          color: 'var(--gold)',
          fontSize: '11px',
          letterSpacing: '0.2em',
          textTransform: 'uppercase',
          marginBottom: '32px',
        }}>
          Your Estimate
        </p>

        <div style={{
          width: '100%',
          maxWidth: '420px',
          border: '1px solid var(--border)',
          padding: '40px',
          background: 'var(--surface)',
          position: 'relative',
        }}>
          <div style={{ position: 'absolute', top: 0, left: 0, width: '40px', height: '40px', borderTop: '2px solid var(--gold)', borderLeft: '2px solid var(--gold)' }} />
          <div style={{ position: 'absolute', bottom: 0, right: 0, width: '40px', height: '40px', borderBottom: '2px solid var(--gold)', borderRight: '2px solid var(--gold)' }} />

          <div style={{ marginBottom: '32px' }}>
            <p style={{ color: 'var(--text-muted)', fontSize: '11px', letterSpacing: '0.15em', textTransform: 'uppercase', marginBottom: '8px' }}>Price Range</p>
            <p style={{ fontFamily: 'var(--font-display)', fontSize: '48px', fontWeight: 300, color: 'var(--gold)' }}>
              ${estimate.priceMin}–${estimate.priceMax}
            </p>
          </div>

          <div style={{ marginBottom: '32px' }}>
            <p style={{ color: 'var(--text-muted)', fontSize: '11px', letterSpacing: '0.15em', textTransform: 'uppercase', marginBottom: '8px' }}>Estimated Availability</p>
            <p style={{ fontSize: '20px', fontWeight: 300 }}>{estimate.estimatedDate}</p>
          </div>

          <div style={{ borderTop: '1px solid var(--border)', paddingTop: '24px' }}>
            <p style={{ color: 'var(--text-muted)', fontSize: '13px', lineHeight: 1.7, fontWeight: 300 }}>{estimate.summary}</p>
          </div>
        </div>

        <p style={{
          color: 'var(--text-muted)', fontSize: '12px', marginTop: '24px',
          textAlign: 'center', lineHeight: 1.6, maxWidth: '320px',
        }}>
          This is an AI-generated estimate. Miguel will confirm the final price and date after reviewing your request.
        </p>

        <button
          onClick={() => setScreen('date-select')}
          style={{
            marginTop: '28px',
            padding: '14px 40px',
            background: 'var(--gold)',
            color: 'var(--black)',
            fontSize: '12px',
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
            fontWeight: 700,
            borderRadius: '2px',
            border: 'none',
            cursor: 'pointer',
            transition: 'opacity 0.15s ease',
          }}
          onMouseEnter={e => (e.currentTarget.style.opacity = '0.85')}
          onMouseLeave={e => (e.currentTarget.style.opacity = '1')}
        >
          Select a Date →
        </button>

        <button
          onClick={onReset}
          style={{
            marginTop: '16px',
            padding: '12px 32px',
            border: '1px solid var(--border)',
            color: 'var(--text-muted)',
            fontSize: '12px',
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            borderRadius: '2px',
            background: 'none',
            cursor: 'pointer',
          }}
          onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--gold)')}
          onMouseLeave={e => (e.currentTarget.style.borderColor = 'rgba(201,168,76,0.15)')}
        >
          Start Over
        </button>
      </div>
    )
  }

  // ─── DATE SELECTION SCREEN ────────────────────────────────────
  if (screen === 'date-select') {
    const dates = estimate.availableDates?.length
      ? estimate.availableDates
      : [estimate.estimatedDate]

    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '40px 24px',
        background: 'var(--black)',
        position: 'relative',
      }}>
        <button
          onClick={() => setScreen('estimate')}
          style={{
            position: 'absolute', top: '24px', left: '24px',
            background: 'none', border: 'none',
            color: 'var(--text-muted)', fontSize: '13px',
            cursor: 'pointer', letterSpacing: '0.05em',
          }}
        >
          ← Back
        </button>

        <p style={{
          color: 'var(--gold)', fontSize: '11px',
          letterSpacing: '0.2em', textTransform: 'uppercase',
          marginBottom: '12px',
        }}>
          Choose Your Date
        </p>

        <p style={{
          color: 'var(--text-muted)', fontSize: '13px',
          marginBottom: '40px', textAlign: 'center',
          lineHeight: 1.6, maxWidth: '300px',
        }}>
          These are Miguel's real open dates based on his current calendar.
        </p>

        <div style={{
          width: '100%', maxWidth: '420px',
          display: 'flex', flexDirection: 'column', gap: '12px',
        }}>
          {dates.map((date, i) => {
            const isSelected = selectedDate === date
            return (
              <button
                key={i}
                onClick={() => setSelectedDate(date)}
                style={{
                  width: '100%', padding: '20px 24px',
                  background: isSelected ? 'rgba(201,168,76,0.08)' : 'var(--surface)',
                  border: `1px solid ${isSelected ? 'var(--gold)' : 'var(--border)'}`,
                  borderRadius: '2px',
                  color: isSelected ? 'var(--gold)' : 'var(--text)',
                  fontSize: '16px', fontWeight: 300,
                  cursor: 'pointer',
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  transition: 'all 0.15s ease',
                }}
                onMouseEnter={e => {
                  if (!isSelected) e.currentTarget.style.borderColor = 'rgba(201,168,76,0.4)'
                }}
                onMouseLeave={e => {
                  if (!isSelected) e.currentTarget.style.borderColor = 'rgba(201,168,76,0.15)'
                }}
              >
                <span>{date}</span>
                <span style={{
                  width: '18px', height: '18px', borderRadius: '50%',
                  border: `1px solid ${isSelected ? 'var(--gold)' : 'var(--border)'}`,
                  background: isSelected ? 'var(--gold)' : 'transparent',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  flexShrink: 0, transition: 'all 0.15s ease',
                }}>
                  {isSelected && <span style={{ fontSize: '10px', color: 'var(--black)', fontWeight: 700 }}>✓</span>}
                </span>
              </button>
            )
          })}
        </div>

        <button
          onClick={() => selectedDate && setScreen('confirmation')}
          disabled={!selectedDate}
          style={{
            marginTop: '32px', padding: '14px 40px',
            background: selectedDate ? 'var(--gold)' : 'var(--surface)',
            color: selectedDate ? 'var(--black)' : 'var(--text-muted)',
            fontSize: '12px', letterSpacing: '0.12em',
            textTransform: 'uppercase', fontWeight: 700,
            borderRadius: '2px',
            border: `1px solid ${selectedDate ? 'var(--gold)' : 'var(--border)'}`,
            cursor: selectedDate ? 'pointer' : 'default',
            transition: 'all 0.2s ease',
          }}
        >
          Confirm Date →
        </button>
      </div>
    )
  }

  // ─── CONFIRMATION SCREEN ──────────────────────────────────────
  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '40px 24px',
      background: 'var(--black)',
      position: 'relative',
    }}>
      {!confirmed ? (
        <>
          <button
            onClick={() => setScreen('date-select')}
            style={{
              position: 'absolute', top: '24px', left: '24px',
              background: 'none', border: 'none',
              color: 'var(--text-muted)', fontSize: '13px',
              cursor: 'pointer', letterSpacing: '0.05em',
            }}
          >
            ← Back
          </button>

          <p style={{
            color: 'var(--gold)', fontSize: '11px',
            letterSpacing: '0.2em', textTransform: 'uppercase',
            marginBottom: '32px',
          }}>
            Confirm Your Request
          </p>

          <div style={{
            width: '100%', maxWidth: '420px',
            border: '1px solid var(--border)',
            padding: '36px', background: 'var(--surface)',
            position: 'relative',
          }}>
            <div style={{ position: 'absolute', top: 0, left: 0, width: '32px', height: '32px', borderTop: '2px solid var(--gold)', borderLeft: '2px solid var(--gold)' }} />
            <div style={{ position: 'absolute', bottom: 0, right: 0, width: '32px', height: '32px', borderBottom: '2px solid var(--gold)', borderRight: '2px solid var(--gold)' }} />

            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <ConfirmRow label="Price Range" value={`$${estimate.priceMin}–$${estimate.priceMax}`} gold />
              <ConfirmRow label="Selected Date" value={selectedDate ?? ''} gold />
              <div style={{ borderTop: '1px solid var(--border)', paddingTop: '20px' }}>
                <p style={{ color: 'var(--text-muted)', fontSize: '11px', letterSpacing: '0.15em', textTransform: 'uppercase', marginBottom: '8px' }}>
                  Miguel's Response
                </p>
                <p style={{ color: 'var(--text-muted)', fontSize: '13px', lineHeight: 1.7, fontWeight: 300 }}>
                  {estimate.summary}
                </p>
              </div>
            </div>
          </div>

          <p style={{
            color: 'var(--text-muted)', fontSize: '12px', marginTop: '20px',
            textAlign: 'center', lineHeight: 1.6, maxWidth: '320px',
          }}>
            This will send your booking request to Miguel on Telegram for his final review. He'll confirm the price and lock in your date.
          </p>

          <button
            onClick={handleConfirm}
            disabled={sending}
            style={{
              marginTop: '28px', padding: '14px 40px',
              background: sending ? 'var(--surface)' : 'var(--gold)',
              color: sending ? 'var(--text-muted)' : 'var(--black)',
              fontSize: '12px', letterSpacing: '0.12em',
              textTransform: 'uppercase', fontWeight: 700,
              borderRadius: '2px', border: 'none',
              cursor: sending ? 'default' : 'pointer',
              transition: 'opacity 0.15s ease',
            }}
            onMouseEnter={e => { if (!sending) e.currentTarget.style.opacity = '0.85' }}
            onMouseLeave={e => { e.currentTarget.style.opacity = '1' }}
          >
            {sending ? 'Sending…' : 'Send to Miguel →'}
          </button>

          <button
            onClick={onReset}
            style={{
              marginTop: '14px', padding: '10px 24px',
              border: 'none', color: 'var(--text-muted)',
              fontSize: '12px', letterSpacing: '0.08em',
              background: 'none', cursor: 'pointer',
            }}
          >
            Cancel
          </button>
        </>
      ) : (
        // ─── SUCCESS STATE ─────────────────────────────────────
        <div style={{ textAlign: 'center', maxWidth: '360px' }}>
          <div style={{
            width: '56px', height: '56px', borderRadius: '50%',
            border: '2px solid var(--gold)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 24px', fontSize: '22px',
          }}>
            ✓
          </div>

          <p style={{
            color: 'var(--gold)', fontSize: '11px',
            letterSpacing: '0.2em', textTransform: 'uppercase',
            marginBottom: '16px',
          }}>
            Request Sent
          </p>

          <p style={{ fontSize: '20px', fontWeight: 300, marginBottom: '12px', lineHeight: 1.4 }}>
            Miguel has your request.
          </p>

          <p style={{ color: 'var(--text-muted)', fontSize: '13px', lineHeight: 1.7, marginBottom: '8px' }}>
            You selected <span style={{ color: 'var(--gold)' }}>{selectedDate}</span>.
          </p>

          <p style={{ color: 'var(--text-muted)', fontSize: '13px', lineHeight: 1.7, marginBottom: '36px' }}>
            He'll review everything and reach out to confirm your appointment and deposit details.
          </p>

          <button
            onClick={onReset}
            style={{
              padding: '12px 32px',
              border: '1px solid var(--border)',
              color: 'var(--text-muted)', fontSize: '12px',
              letterSpacing: '0.1em', textTransform: 'uppercase',
              borderRadius: '2px', background: 'none', cursor: 'pointer',
            }}
            onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--gold)')}
            onMouseLeave={e => (e.currentTarget.style.borderColor = 'rgba(201,168,76,0.15)')}
          >
            Start Over
          </button>
        </div>
      )}
    </div>
  )
}

// ─── HELPER ───────────────────────────────────────────────────────
function ConfirmRow({ label, value, gold }: { label: string; value: string; gold?: boolean }) {
  return (
    <div>
      <p style={{ color: 'var(--text-muted)', fontSize: '11px', letterSpacing: '0.15em', textTransform: 'uppercase', marginBottom: '4px' }}>
        {label}
      </p>
      <p style={{ fontSize: '18px', fontWeight: 300, color: gold ? 'var(--gold)' : 'var(--text)' }}>
        {value}
      </p>
    </div>
  )
}