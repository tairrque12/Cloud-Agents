// src/components/EstimateCard.tsx
// Inkbook — Estimate → Date Selection → Confirmation flow
// Updated:
//   - Soft note on date-select screen when offered dates may
//     exceed the client's preferred timeframe (e.g. they asked
//     for "within 2 weeks" but Miguel's first opening is 3 weeks out)
//   - "None of these dates work" path with NEEDS_ALTERNATE sentinel

import { useState } from 'react'
import type { Estimate } from '../App'

interface Props {
  estimate: Estimate
  onReset: () => void
}

type Screen = 'estimate' | 'date-select' | 'confirmation'

const NEEDS_ALTERNATE = 'NEEDS_ALTERNATE'

// ─── TIMEFRAME WINDOWS ────────────────────────────────────────────
// Maximum days from today that each preferred timing label allows.
// If the offered dates exceed this window, we show a soft note.
const TIMEFRAME_DAYS: Record<string, number> = {
  within_2_weeks: 14,
  within_1_month: 31,
  within_2_months: 62,
  flexible: 9999,
}

const TIMEFRAME_LABEL: Record<string, string> = {
  within_2_weeks: 'within 2 weeks',
  within_1_month: 'within 1 month',
  within_2_months: 'within 2 months',
  flexible: 'flexible',
}

// Parse "Saturday · May 10" → Date object for the upcoming occurrence.
// Returns null if parsing fails.
function parseOfferedDate(formatted: string): Date | null {
  // Match "May 10" portion
  const match = formatted.match(/([A-Za-z]+)\s+(\d{1,2})/)
  if (!match) return null
  const monthName = match[1]
  const day = parseInt(match[2], 10)
  const months = ['January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December']
  const monthIdx = months.findIndex(m => m.toLowerCase() === monthName.toLowerCase())
  if (monthIdx < 0) return null

  const today = new Date()
  let year = today.getFullYear()
  // If the parsed month/day is before today, assume next year
  const candidate = new Date(year, monthIdx, day)
  if (candidate < today) {
    candidate.setFullYear(year + 1)
  }
  return candidate
}

// Returns true if the EARLIEST offered date is later than the client's window
function offeredDatesExceedTimeframe(
  dates: string[],
  preferredTiming: string
): boolean {
  if (!preferredTiming || preferredTiming === 'flexible') return false
  const maxDays = TIMEFRAME_DAYS[preferredTiming] ?? 9999

  const today = new Date()
  today.setHours(0, 0, 0, 0)

  for (const d of dates) {
    const parsed = parseOfferedDate(d)
    if (!parsed) continue
    const diffDays = Math.floor((parsed.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
    if (diffDays <= maxDays) return false  // at least one date is in window
  }
  // Every date is outside the window
  return true
}

export default function EstimateCard({ estimate, onReset }: Props) {
  const [screen, setScreen] = useState<Screen>('estimate')
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [needsAlternate, setNeedsAlternate] = useState(false)
  const [confirmed, setConfirmed] = useState(false)
  const [sending, setSending] = useState(false)

  const datesExceedWindow = offeredDatesExceedTimeframe(
    estimate.availableDates ?? [],
    estimate.preferredTiming ?? ''
  )

  const handleConfirm = async () => {
    if (sending) return
    if (!needsAlternate && !selectedDate) return

    const dateToSend = needsAlternate ? NEEDS_ALTERNATE : (selectedDate as string)

    setSending(true)
    try {
      await fetch('https://inkbook-4tlr.onrender.com/api/miguel/confirm-date', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          intake_id: estimate.intakeId,
          selected_date: dateToSend,
        }),
      })
    } catch {
      // non-fatal
    } finally {
      setSending(false)
      setConfirmed(true)
    }
  }

  const pickDate = (date: string) => {
    setSelectedDate(date)
    setNeedsAlternate(false)
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

    const canContinue = needsAlternate || selectedDate !== null
    const preferredLabel = TIMEFRAME_LABEL[estimate.preferredTiming ?? ''] ?? ''

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
          marginBottom: datesExceedWindow ? '16px' : '40px',
          textAlign: 'center',
          lineHeight: 1.6, maxWidth: '320px',
        }}>
          These are Miguel's real open dates based on his current calendar.
        </p>

        {/* ── Timeframe mismatch note ──────────────────────────── */}
        {datesExceedWindow && (
          <div style={{
            maxWidth: '420px',
            width: '100%',
            padding: '14px 18px',
            marginBottom: '32px',
            background: 'rgba(201,168,76,0.05)',
            border: '1px solid rgba(201,168,76,0.25)',
            borderRadius: '4px',
          }}>
            <p style={{
              color: 'var(--gold)', fontSize: '11px',
              letterSpacing: '0.12em', textTransform: 'uppercase',
              marginBottom: '6px', fontWeight: 600,
            }}>
              Heads Up
            </p>
            <p style={{
              color: 'var(--text-muted)', fontSize: '12px',
              lineHeight: 1.6, fontWeight: 300,
            }}>
              You requested a tattoo {preferredLabel}, but these are Miguel's soonest open dates.
              Pick the closest one that works, or let him know none of these fit and he'll reach
              out personally to find something that matches your schedule.
            </p>
          </div>
        )}

        <div style={{
          width: '100%', maxWidth: '420px',
          display: 'flex', flexDirection: 'column', gap: '12px',
        }}>
          {dates.map((date, i) => {
            const isSelected = !needsAlternate && selectedDate === date
            return (
              <button
                key={i}
                onClick={() => pickDate(date)}
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

          {/* ── None of these dates work option ─────────────────── */}
          <div style={{
            margin: '8px 0 4px',
            display: 'flex', alignItems: 'center',
            gap: '12px',
          }}>
            <div style={{ flex: 1, height: '1px', background: 'var(--border)' }} />
            <span style={{ color: 'var(--text-muted)', fontSize: '11px', letterSpacing: '0.1em' }}>OR</span>
            <div style={{ flex: 1, height: '1px', background: 'var(--border)' }} />
          </div>

          <button
            onClick={() => {
              setNeedsAlternate(true)
              setSelectedDate(null)
            }}
            style={{
              width: '100%', padding: '20px 24px',
              background: needsAlternate ? 'rgba(201,168,76,0.08)' : 'var(--surface)',
              border: `1px solid ${needsAlternate ? 'var(--gold)' : 'var(--border)'}`,
              borderRadius: '2px',
              color: needsAlternate ? 'var(--gold)' : 'var(--text)',
              fontSize: '15px', fontWeight: 300,
              cursor: 'pointer',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              transition: 'all 0.15s ease',
              textAlign: 'left',
            }}
            onMouseEnter={e => {
              if (!needsAlternate) e.currentTarget.style.borderColor = 'rgba(201,168,76,0.4)'
            }}
            onMouseLeave={e => {
              if (!needsAlternate) e.currentTarget.style.borderColor = 'rgba(201,168,76,0.15)'
            }}
          >
            <span>None of these dates work for me</span>
            <span style={{
              width: '18px', height: '18px', borderRadius: '50%',
              border: `1px solid ${needsAlternate ? 'var(--gold)' : 'var(--border)'}`,
              background: needsAlternate ? 'var(--gold)' : 'transparent',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0, transition: 'all 0.15s ease',
            }}>
              {needsAlternate && <span style={{ fontSize: '10px', color: 'var(--black)', fontWeight: 700 }}>✓</span>}
            </span>
          </button>

          {needsAlternate && (
            <p style={{
              color: 'var(--text-muted)', fontSize: '12px',
              lineHeight: 1.6, marginTop: '4px',
              padding: '0 4px', textAlign: 'center',
            }}>
              No problem. Miguel will review your request and reach out personally to coordinate a date that works for you.
            </p>
          )}
        </div>

        <button
          onClick={() => canContinue && setScreen('confirmation')}
          disabled={!canContinue}
          style={{
            marginTop: '32px', padding: '14px 40px',
            background: canContinue ? 'var(--gold)' : 'var(--surface)',
            color: canContinue ? 'var(--black)' : 'var(--text-muted)',
            fontSize: '12px', letterSpacing: '0.12em',
            textTransform: 'uppercase', fontWeight: 700,
            borderRadius: '2px',
            border: `1px solid ${canContinue ? 'var(--gold)' : 'var(--border)'}`,
            cursor: canContinue ? 'pointer' : 'default',
            transition: 'all 0.2s ease',
          }}
        >
          {needsAlternate ? 'Continue →' : 'Confirm Date →'}
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
              {needsAlternate ? (
                <ConfirmRow label="Date" value="Awaiting Miguel's outreach" gold />
              ) : (
                <ConfirmRow label="Selected Date" value={selectedDate ?? ''} gold />
              )}
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
            textAlign: 'center', lineHeight: 1.6, maxWidth: '340px',
          }}>
            {needsAlternate
              ? "Miguel will review your request and reach out personally to find a date that works for you."
              : "This will send your booking request to Miguel on Telegram for his final review. He'll confirm the price and lock in your date."}
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
        <div style={{ textAlign: 'center', maxWidth: '380px' }}>
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

          {needsAlternate ? (
            <p style={{ color: 'var(--text-muted)', fontSize: '13px', lineHeight: 1.7, marginBottom: '36px' }}>
              He'll review everything and reach out personally to coordinate a date that works for your schedule.
            </p>
          ) : (
            <>
              <p style={{ color: 'var(--text-muted)', fontSize: '13px', lineHeight: 1.7, marginBottom: '8px' }}>
                You selected <span style={{ color: 'var(--gold)' }}>{selectedDate}</span>.
              </p>
              <p style={{ color: 'var(--text-muted)', fontSize: '13px', lineHeight: 1.7, marginBottom: '36px' }}>
                He'll review everything and reach out to confirm your appointment and deposit details.
              </p>
            </>
          )}

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