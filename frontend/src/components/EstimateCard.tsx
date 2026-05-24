// src/components/EstimateCard.tsx
// Inkbook — Estimate → Date Selection → Confirmation flow
// Mobile fixes:
//   - Added paddingTop to estimate screen so YOUR ESTIMATE label isn't clipped
//   - Date picker cards use width: 100% and box-sizing: border-box
//   - Consistent mobile spacing throughout

import { useState } from 'react'
import type { Estimate } from '../App'
import type { ArtistProfile } from '../types/artist'
import { artistApiPath } from '../config'

interface Props {
  artist: ArtistProfile
  artistSlug: string
  estimate: Estimate
  onReset: () => void
}

type Screen = 'estimate' | 'date-select' | 'confirmation'

const NEEDS_ALTERNATE = 'NEEDS_ALTERNATE'

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

function parseOfferedDate(formatted: string): Date | null {
  const match = formatted.match(/([A-Za-z]+)\s+(\d{1,2})/)
  if (!match) return null
  const monthName = match[1]
  const day = parseInt(match[2], 10)
  const months = ['January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December']
  const monthIdx = months.findIndex(m => m.toLowerCase() === monthName.toLowerCase())
  if (monthIdx < 0) return null
  const today = new Date()
  const candidate = new Date(today.getFullYear(), monthIdx, day)
  if (candidate < today) candidate.setFullYear(today.getFullYear() + 1)
  return candidate
}

function offeredDatesExceedTimeframe(dates: string[], preferredTiming: string): boolean {
  if (!preferredTiming || preferredTiming === 'flexible') return false
  const maxDays = TIMEFRAME_DAYS[preferredTiming] ?? 9999
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  for (const d of dates) {
    const parsed = parseOfferedDate(d)
    if (!parsed) continue
    const diffDays = Math.floor((parsed.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
    if (diffDays <= maxDays) return false
  }
  return true
}

export default function EstimateCard({ artist, artistSlug, estimate, onReset }: Props) {
  const artistName = artist.name
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
      await fetch(artistApiPath(artistSlug, 'confirm-date'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ intake_id: estimate.intakeId, selected_date: dateToSend }),
      })
    } catch { /* non-fatal */ } finally {
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
        // Extra top padding so "YOUR ESTIMATE" label isn't clipped on mobile
        padding: '80px 20px 40px',
        background: 'var(--black)',
        boxSizing: 'border-box',
      }}>
        <p style={{
          color: 'var(--gold)', fontSize: '11px',
          letterSpacing: '0.2em', textTransform: 'uppercase',
          marginBottom: '28px',
        }}>
          Your Estimate
        </p>

        <div style={{
          width: '100%',
          maxWidth: '420px',
          border: '1px solid var(--border)',
          padding: '32px 28px',
          background: 'var(--surface)',
          position: 'relative',
          boxSizing: 'border-box',
        }}>
          <div style={{ position: 'absolute', top: 0, left: 0, width: '36px', height: '36px', borderTop: '2px solid var(--gold)', borderLeft: '2px solid var(--gold)' }} />
          <div style={{ position: 'absolute', bottom: 0, right: 0, width: '36px', height: '36px', borderBottom: '2px solid var(--gold)', borderRight: '2px solid var(--gold)' }} />

          <div style={{ marginBottom: '28px' }}>
            <p style={{ color: 'var(--text-muted)', fontSize: '11px', letterSpacing: '0.15em', textTransform: 'uppercase', marginBottom: '8px' }}>Price Range</p>
            <p style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(36px, 8vw, 48px)', fontWeight: 300, color: 'var(--gold)' }}>
              ${estimate.priceMin}–${estimate.priceMax}
            </p>
          </div>

          <div style={{ marginBottom: '28px' }}>
            <p style={{ color: 'var(--text-muted)', fontSize: '11px', letterSpacing: '0.15em', textTransform: 'uppercase', marginBottom: '8px' }}>Estimated Availability</p>
            <p style={{ fontSize: '18px', fontWeight: 300 }}>{estimate.estimatedDate}</p>
          </div>

          <div style={{ borderTop: '1px solid var(--border)', paddingTop: '20px' }}>
            <p style={{ color: 'var(--text-muted)', fontSize: '13px', lineHeight: 1.7, fontWeight: 300 }}>{estimate.summary}</p>
          </div>
        </div>

        <p style={{
          color: 'var(--text-muted)', fontSize: '12px', marginTop: '20px',
          textAlign: 'center', lineHeight: 1.6, maxWidth: '300px',
          padding: '0 4px',
        }}>
          This is an AI-generated estimate. {artistName} will confirm the final price and date after reviewing your request.
        </p>

        <button
          onClick={() => setScreen('date-select')}
          style={{
            marginTop: '24px', padding: '14px 0',
            background: 'var(--gold)', color: 'var(--black)',
            fontSize: '12px', letterSpacing: '0.12em',
            textTransform: 'uppercase', fontWeight: 700,
            borderRadius: '2px', border: 'none', cursor: 'pointer',
            width: '100%', maxWidth: '420px',
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
            marginTop: '12px', padding: '12px 0',
            border: '1px solid var(--border)', color: 'var(--text-muted)',
            fontSize: '12px', letterSpacing: '0.1em',
            textTransform: 'uppercase', borderRadius: '2px',
            background: 'none', cursor: 'pointer',
            width: '100%', maxWidth: '420px',
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
        padding: '80px 20px 40px',
        background: 'var(--black)',
        position: 'relative',
        boxSizing: 'border-box',
      }}>
        <button
          onClick={() => setScreen('estimate')}
          style={{
            position: 'absolute', top: '24px', left: '20px',
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
          marginBottom: '10px',
        }}>
          Choose Your Date
        </p>

        <p style={{
          color: 'var(--text-muted)', fontSize: '13px',
          marginBottom: datesExceedWindow ? '16px' : '32px',
          textAlign: 'center', lineHeight: 1.6, maxWidth: '300px',
        }}>
          These are {artistName}'s real open dates based on their current calendar.
        </p>

        {datesExceedWindow && (
          <div style={{
            width: '100%', maxWidth: '420px',
            padding: '14px 16px', marginBottom: '24px',
            background: 'rgba(201,168,76,0.05)',
            border: '1px solid rgba(201,168,76,0.25)',
            borderRadius: '4px', boxSizing: 'border-box',
          }}>
            <p style={{
              color: 'var(--gold)', fontSize: '11px',
              letterSpacing: '0.12em', textTransform: 'uppercase',
              marginBottom: '6px', fontWeight: 600,
            }}>Heads Up</p>
            <p style={{ color: 'var(--text-muted)', fontSize: '12px', lineHeight: 1.6, fontWeight: 300 }}>
              You requested {preferredLabel}, but these are {artistName}'s soonest open dates.
              Pick the closest one or let him know none work and he'll reach out personally.
            </p>
          </div>
        )}

        {/* Date options — full width */}
        <div style={{
          width: '100%', maxWidth: '420px',
          display: 'flex', flexDirection: 'column', gap: '10px',
          boxSizing: 'border-box',
        }}>
          {dates.map((date, i) => {
            const isSelected = !needsAlternate && selectedDate === date
            return (
              <button
                key={i}
                onClick={() => pickDate(date)}
                style={{
                  width: '100%', padding: '18px 20px',
                  background: isSelected ? 'rgba(201,168,76,0.08)' : 'var(--surface)',
                  border: `1px solid ${isSelected ? 'var(--gold)' : 'var(--border)'}`,
                  borderRadius: '2px',
                  color: isSelected ? 'var(--gold)' : 'var(--text)',
                  fontSize: '15px', fontWeight: 300,
                  cursor: 'pointer', boxSizing: 'border-box',
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  transition: 'all 0.15s ease', textAlign: 'left',
                }}
                onMouseEnter={e => { if (!isSelected) e.currentTarget.style.borderColor = 'rgba(201,168,76,0.4)' }}
                onMouseLeave={e => { if (!isSelected) e.currentTarget.style.borderColor = 'rgba(201,168,76,0.15)' }}
              >
                <span>{date}</span>
                <span style={{
                  width: '18px', height: '18px', borderRadius: '50%', flexShrink: 0,
                  border: `1px solid ${isSelected ? 'var(--gold)' : 'var(--border)'}`,
                  background: isSelected ? 'var(--gold)' : 'transparent',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  transition: 'all 0.15s ease',
                }}>
                  {isSelected && <span style={{ fontSize: '10px', color: 'var(--black)', fontWeight: 700 }}>✓</span>}
                </span>
              </button>
            )
          })}

          {/* OR divider */}
          <div style={{ margin: '4px 0', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ flex: 1, height: '1px', background: 'var(--border)' }} />
            <span style={{ color: 'var(--text-muted)', fontSize: '11px', letterSpacing: '0.1em' }}>OR</span>
            <div style={{ flex: 1, height: '1px', background: 'var(--border)' }} />
          </div>

          {/* None of these work */}
          <button
            onClick={() => { setNeedsAlternate(true); setSelectedDate(null) }}
            style={{
              width: '100%', padding: '18px 20px', boxSizing: 'border-box',
              background: needsAlternate ? 'rgba(201,168,76,0.08)' : 'var(--surface)',
              border: `1px solid ${needsAlternate ? 'var(--gold)' : 'var(--border)'}`,
              borderRadius: '2px',
              color: needsAlternate ? 'var(--gold)' : 'var(--text)',
              fontSize: '14px', fontWeight: 300, cursor: 'pointer',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              transition: 'all 0.15s ease', textAlign: 'left',
            }}
            onMouseEnter={e => { if (!needsAlternate) e.currentTarget.style.borderColor = 'rgba(201,168,76,0.4)' }}
            onMouseLeave={e => { if (!needsAlternate) e.currentTarget.style.borderColor = 'rgba(201,168,76,0.15)' }}
          >
            <span>None of these dates work for me</span>
            <span style={{
              width: '18px', height: '18px', borderRadius: '50%', flexShrink: 0,
              border: `1px solid ${needsAlternate ? 'var(--gold)' : 'var(--border)'}`,
              background: needsAlternate ? 'var(--gold)' : 'transparent',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              transition: 'all 0.15s ease',
            }}>
              {needsAlternate && <span style={{ fontSize: '10px', color: 'var(--black)', fontWeight: 700 }}>✓</span>}
            </span>
          </button>

          {needsAlternate && (
            <p style={{
              color: 'var(--text-muted)', fontSize: '12px',
              lineHeight: 1.6, padding: '0 4px', textAlign: 'center',
            }}>
              No problem. {artistName} will review your request and reach out personally to coordinate a date that works for you.
            </p>
          )}
        </div>

        <button
          onClick={() => canContinue && setScreen('confirmation')}
          disabled={!canContinue}
          style={{
            marginTop: '24px', padding: '14px 0',
            background: canContinue ? 'var(--gold)' : 'var(--surface)',
            color: canContinue ? 'var(--black)' : 'var(--text-muted)',
            fontSize: '12px', letterSpacing: '0.12em',
            textTransform: 'uppercase', fontWeight: 700,
            borderRadius: '2px',
            border: `1px solid ${canContinue ? 'var(--gold)' : 'var(--border)'}`,
            cursor: canContinue ? 'pointer' : 'default',
            width: '100%', maxWidth: '420px',
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
      padding: '80px 20px 40px',
      background: 'var(--black)',
      position: 'relative',
      boxSizing: 'border-box',
    }}>
      {!confirmed ? (
        <>
          <button
            onClick={() => setScreen('date-select')}
            style={{
              position: 'absolute', top: '24px', left: '20px',
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
            marginBottom: '28px',
          }}>
            Confirm Your Request
          </p>

          <div style={{
            width: '100%', maxWidth: '420px',
            border: '1px solid var(--border)',
            padding: '28px 24px', background: 'var(--surface)',
            position: 'relative', boxSizing: 'border-box',
          }}>
            <div style={{ position: 'absolute', top: 0, left: 0, width: '28px', height: '28px', borderTop: '2px solid var(--gold)', borderLeft: '2px solid var(--gold)' }} />
            <div style={{ position: 'absolute', bottom: 0, right: 0, width: '28px', height: '28px', borderBottom: '2px solid var(--gold)', borderRight: '2px solid var(--gold)' }} />

            <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
              <ConfirmRow label="Price Range" value={`$${estimate.priceMin}–$${estimate.priceMax}`} gold />
              {needsAlternate
                ? <ConfirmRow label="Date" value={`Awaiting ${artistName}'s outreach`} gold />
                : <ConfirmRow label="Selected Date" value={selectedDate ?? ''} gold />
              }
              <div style={{ borderTop: '1px solid var(--border)', paddingTop: '18px' }}>
                <p style={{ color: 'var(--text-muted)', fontSize: '11px', letterSpacing: '0.15em', textTransform: 'uppercase', marginBottom: '8px' }}>
                  {artistName}'s Response
                </p>
                <p style={{ color: 'var(--text-muted)', fontSize: '13px', lineHeight: 1.7, fontWeight: 300 }}>
                  {estimate.summary}
                </p>
              </div>
            </div>
          </div>

          <p style={{
            color: 'var(--text-muted)', fontSize: '12px', marginTop: '18px',
            textAlign: 'center', lineHeight: 1.6, maxWidth: '320px', padding: '0 4px',
          }}>
            {needsAlternate
              ? `${artistName} will review your request and reach out personally to find a date that works for you.`
              : `This sends your request to ${artistName} for review. They'll confirm the price and lock in your date.`}
          </p>

          <button
            onClick={handleConfirm}
            disabled={sending}
            style={{
              marginTop: '24px', padding: '14px 0',
              background: sending ? 'var(--surface)' : 'var(--gold)',
              color: sending ? 'var(--text-muted)' : 'var(--black)',
              fontSize: '12px', letterSpacing: '0.12em',
              textTransform: 'uppercase', fontWeight: 700,
              borderRadius: '2px', border: 'none',
              cursor: sending ? 'default' : 'pointer',
              width: '100%', maxWidth: '420px',
              transition: 'opacity 0.15s ease',
            }}
            onMouseEnter={e => { if (!sending) e.currentTarget.style.opacity = '0.85' }}
            onMouseLeave={e => { e.currentTarget.style.opacity = '1' }}
          >
            {sending ? 'Sending…' : `Send to ${artistName} →`}
          </button>

          <button
            onClick={onReset}
            style={{
              marginTop: '12px', padding: '10px',
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
        <div style={{ textAlign: 'center', maxWidth: '340px', padding: '0 4px' }}>
          <div style={{
            width: '52px', height: '52px', borderRadius: '50%',
            border: '2px solid var(--gold)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 20px', fontSize: '20px',
          }}>
            ✓
          </div>

          <p style={{
            color: 'var(--gold)', fontSize: '11px',
            letterSpacing: '0.2em', textTransform: 'uppercase',
            marginBottom: '14px',
          }}>
            Request Sent
          </p>

          <p style={{ fontSize: '20px', fontWeight: 300, marginBottom: '12px', lineHeight: 1.4 }}>
            {artistName} has your request.
          </p>

          {needsAlternate ? (
            <p style={{ color: 'var(--text-muted)', fontSize: '13px', lineHeight: 1.7, marginBottom: '32px' }}>
              He'll review everything and reach out personally to coordinate a date that works for your schedule.
            </p>
          ) : (
            <>
              <p style={{ color: 'var(--text-muted)', fontSize: '13px', lineHeight: 1.7, marginBottom: '6px' }}>
                You selected <span style={{ color: 'var(--gold)' }}>{selectedDate}</span>.
              </p>
              <p style={{ color: 'var(--text-muted)', fontSize: '13px', lineHeight: 1.7, marginBottom: '32px' }}>
                He'll review everything and reach out to confirm your appointment and deposit details.
              </p>
            </>
          )}

          <button
            onClick={onReset}
            style={{
              padding: '12px 0', width: '100%',
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

function ConfirmRow({ label, value, gold }: { label: string; value: string; gold?: boolean }) {
  return (
    <div>
      <p style={{ color: 'var(--text-muted)', fontSize: '11px', letterSpacing: '0.15em', textTransform: 'uppercase', marginBottom: '4px' }}>
        {label}
      </p>
      <p style={{ fontSize: '17px', fontWeight: 300, color: gold ? 'var(--gold)' : 'var(--text)' }}>
        {value}
      </p>
    </div>
  )
}