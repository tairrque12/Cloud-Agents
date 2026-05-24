// src/components/ChatWindow.tsx
// Inkbook — Chat intake flow
//
// COVERAGE CHIPS UPDATE:
// Removed "size" step (small/medium/large was ambiguous).
// Replaced with "coverage" step that fires after placement.
// Question is dynamic: "How much of your [placement] are you looking to cover?"
// Full sleeve/leg placements skip coverage entirely (already implied).
// Backend receives coverage + placement to determine session type.
// Miguel sees placement + coverage on his Telegram card.

import { useState, useRef, useEffect } from 'react'
import type { Estimate } from '../App'
import type { ArtistProfile } from '../types/artist'
import { artistApiPath } from '../config'

interface Message {
  role: 'assistant' | 'user'
  content: string
  chips?: ChipOption[]
  isUpload?: boolean
  stepKey?: string
  fullWidthChips?: boolean
}

type ChipOption = string | { label: string; description: string }

interface Props {
  artist: ArtistProfile | null
  artistSlug: string
  onComplete: (estimate: Estimate) => void
}

function buildIntro(artist: ArtistProfile | null): string {
  if (!artist) {
    return "Hey! Tell me what you're looking to get done."
  }
  const location = artist.location || artist.city || 'your area'
  const bio = artist.bio_short || `tattoo artist based in ${location}.`
  return `Hey! I'm ${artist.name} — ${bio} What are you looking to get done?`
}

function referencePrompt(artistName: string): string {
  return `Upload up to 3 reference images. Photos help ${artistName} give a more accurate quote and prepare for your session.`
}

type Step =
  | 'description' | 'placement' | 'coverage' | 'style' | 'coverup'
  | 'reference' | 'budget' | 'timeline' | 'name' | 'contact' | 'processing'

const STEP_SEQUENCE: Step[] = [
  'description', 'placement', 'coverage', 'reference', 'name', 'contact', 'processing',
]

// Progress indicator — one dot per intake step (excludes processing)
const PROGRESS_STEPS = ['description', 'placement', 'coverage', 'reference', 'name', 'contact'] as const
type ProgressStep = (typeof PROGRESS_STEPS)[number]

const PROGRESS_LABELS: Record<ProgressStep, string> = {
  description: 'Tell us your idea',
  placement: 'Placement',
  coverage: 'Coverage',
  reference: 'Reference images',
  name: 'Your name',
  contact: 'Contact info',
}

// Placements where coverage is already implied — skip the coverage step
const SKIP_COVERAGE_PLACEMENTS = new Set([
  'Full Arm Sleeve',
  'Full Leg Sleeve',
])

const FULL_WIDTH_CHIP_STEPS: Set<Step> = new Set(['coverage'])
// const FULL_WIDTH_CHIP_STEPS: Set<Step> = new Set(['coverage', 'budget', 'timeline'])

// Coverage chips — placement label is interpolated into the question dynamically
const COVERAGE_CHIPS: ChipOption[] = [
  { label: 'Just a section',    description: 'Partial coverage · smaller piece' },
  { label: 'Most of it',        description: 'Majority coverage · medium to large piece' },
  { label: 'The whole thing',   description: 'Full coverage · larger commitment' },
]

// Coverage → session type mapping used for fallback pricing
// placement is also factored in for back/chest/torso
const COVERAGE_TO_SESSION: Record<string, Record<string, string>> = {
  'just a section': {
    default: 'small',
    back: 'half_day',
    chest: 'half_day',
    torso: 'half_day',
  },
  'most of it': {
    default: 'half_day',
    back: 'full_day',
    chest: 'full_day',
    torso: 'full_day',
  },
  'the whole thing': {
    default: 'full_day',
    back: 'full_day',
    chest: 'full_day',
    torso: 'full_day',
  },
}

function getCoverageSession(coverage: string, placement: string): string {
  const coverageKey = coverage.toLowerCase()
  const placementKey = placement.toLowerCase()
  const map = COVERAGE_TO_SESSION[coverageKey] ?? {}
  // Check if placement matches a specific key
  for (const key of Object.keys(map)) {
    if (key !== 'default' && placementKey.includes(key)) {
      return map[key]
    }
  }
  return map['default'] ?? 'half_day'
}

const STEP_QUESTIONS: Partial<Record<Step, string>> = {
  // coverage question is generated dynamically in advanceStep
  placement: 'Where on your body do you want this tattoo?',
  name: "What's your name?",
  contact: "What's the best phone number to reach you?",
  reference: "Upload up to 3 reference images. Photos help Miguel give a more accurate quote and prepare for your session.",
  // style: 'What style are you drawn to?',
  // coverup: 'Is this a cover up of an existing tattoo?',
  // budget: "What's your rough budget for this piece?",
  // timeline: 'When are you looking to get this done?',
}

const CHIPS: Partial<Record<Step, ChipOption[]>> = {
  placement: [
    'Forearm', 'Upper Arm', 'Full Arm Sleeve',
    'Chest', 'Back',
    'Leg', 'Full Leg Sleeve',
    'Torso', 'Hand', 'Neck', 'Other'
  ],
  // style: ['Realism', 'Traditional', 'Fine Line', 'Geometric', 'Blackwork', 'Not Sure'],
  // coverup: ['Yes', 'No'],
  // budget: ['Under $200', '$200–$500', '$500–$1,000', '$1,000+'],
  // timeline: ['Within 2 weeks', 'Within 1 month', 'Within 2 months', 'Flexible'],
}

const MAX_IMAGES = 3

function chipValue(chip: ChipOption): string {
  const label = typeof chip === 'string' ? chip : chip.label
  return label.replace(/\s*\(.*?\)\s*/g, '').trim()
}

function chipLabel(chip: ChipOption): string {
  return typeof chip === 'string' ? chip : chip.label
}

function chipDescription(chip: ChipOption): string | null {
  return typeof chip === 'string' ? null : chip.description
}

const DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
const MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December']

function parseAvailableDates(text: string): string[] {
  const dates: string[] = []
  const seen = new Set<string>()
  const pattern = new RegExp(
    `(${DAY_NAMES.join('|')})[,\\s·]+((${MONTH_NAMES.join('|')})\\s+\\d{1,2})`,
    'g'
  )
  let match
  while ((match = pattern.exec(text)) !== null) {
    const formatted = `${match[1]} · ${match[2]}`
    if (!seen.has(formatted)) {
      seen.add(formatted)
      dates.push(formatted)
    }
  }
  return dates
}

const FALLBACK_PRICING: Record<string, { min: number; max: number }> = {
  small:       { min: 100, max: 300 },
  half_day:    { min: 400, max: 600 },
  full_day:    { min: 800, max: 1000 },
  full_sleeve: { min: 800, max: 1000 },
}

export default function ChatWindow({ artist, artistSlug, onComplete }: Props) {
  const artistName = artist?.name ?? 'your artist'
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: buildIntro(artist),
    }
  ])
  const [step, setStep] = useState<Step>('description')
  const [input, setInput] = useState('')
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [referenceImages, setReferenceImages] = useState<string[]>([])
  const [uploadDone, setUploadDone] = useState(false)
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    setMessages([{ role: 'assistant', content: buildIntro(artist) }])
    setStep('description')
    setAnswers({})
    setReferenceImages([])
    setUploadDone(false)
  }, [artistSlug, artist?.slug])

  useEffect(() => {
    const t = setTimeout(
      () => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }),
      100
    )
    return () => clearTimeout(t)
  }, [messages, loading])

  const addAssistantMessage = (content: string, extras?: Partial<Message>) => {
    setMessages(prev => [...prev, { role: 'assistant', content, ...extras }])
  }

  const addUserMessage = (content: string) => {
    setMessages(prev => [...prev, { role: 'user', content }])
  }

  const advanceStep = (
    currentStep: Step,
    answer: string,
    newAnswersOverride?: Record<string, string>
  ) => {
    let newAnswers = { ...(newAnswersOverride ?? answers), [currentStep]: answer }

    const idx = STEP_SEQUENCE.indexOf(currentStep)
    let nextStep = STEP_SEQUENCE[idx + 1] as Step

    // Skip coverage step for full sleeve/leg placements
    if (currentStep === 'placement' && SKIP_COVERAGE_PLACEMENTS.has(answer)) {
      // Set coverage to 'full' implicitly so backend has the value
      newAnswers = { ...newAnswers, coverage: 'full' }
      nextStep = 'reference'
    }

    setAnswers(newAnswers)
    setStep(nextStep)

    setTimeout(() => {
      if (nextStep === 'processing') {
        submitToBackend(newAnswers)
      } else if (nextStep === 'reference') {
        setUploadDone(false)
        const question = referencePrompt(artistName)
        addAssistantMessage(question, {
          isUpload: true,
          stepKey: 'reference',
        })
      } else if (nextStep === 'coverage') {
        // Dynamic coverage question based on placement
        const placement = newAnswers['placement'] ?? 'that area'
        const placementLower = placement.toLowerCase()
        // Build a natural question
        const question = `How much of your ${placementLower} are you looking to cover?`
        addAssistantMessage(question, {
          chips: COVERAGE_CHIPS,
          stepKey: 'coverage',
          fullWidthChips: true,
        })
      } else {
        const question = STEP_QUESTIONS[nextStep]!
        const chips = CHIPS[nextStep]
        const fullWidthChips = FULL_WIDTH_CHIP_STEPS.has(nextStep)
        addAssistantMessage(question, {
          chips,
          stepKey: nextStep,
          fullWidthChips,
        })
      }
    }, 500)
  }

  const handleSend = () => {
    const text = input.trim()
    if (!text || loading) return
    setInput('')
    addUserMessage(text)
    advanceStep(step, text)
  }

  const handleChip = (chip: ChipOption, stepKey: string) => {
    if (stepKey !== step) return
    const value = chipValue(chip)
    addUserMessage(chipLabel(chip))
    advanceStep(step, value)
  }

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? [])
    if (!files.length) return
    e.target.value = ''
    const remaining = MAX_IMAGES - referenceImages.length
    const toProcess = files.slice(0, remaining)
    toProcess.forEach(file => {
      const reader = new FileReader()
      reader.onload = () => {
        const dataUrl = reader.result as string
        setReferenceImages(prev => {
          if (prev.length >= MAX_IMAGES) return prev
          return [...prev, dataUrl]
        })
      }
      reader.readAsDataURL(file)
    })
  }

  const handleUploadDone = () => {
    if (uploadDone) return
    setUploadDone(true)
    const count = referenceImages.length
    const label = count === 0
      ? 'No reference image uploaded'
      : count === 1 ? '📎 1 reference image uploaded'
      : `📎 ${count} reference images uploaded`
    addUserMessage(label)
    advanceStep('reference', count > 0 ? 'uploaded' : 'skipped')
  }

  const submitToBackend = async (finalAnswers: Record<string, string>) => {
    setLoading(true)
    setTimeout(() => addAssistantMessage('⚡ Analyzing your request… ✓'), 400)
    setTimeout(() => addAssistantMessage('📅 Checking artist availability… ✓'), 1200)
    setTimeout(() => addAssistantMessage('💰 Preparing your estimate… ✓'), 2000)

    const placement = finalAnswers.placement ?? 'not specified'
    const coverage = finalAnswers.coverage ?? 'not specified'

    // Determine session type from placement + coverage
    const isSleevePlacement = placement.toLowerCase().includes('sleeve')
    const isLegSleevePlace = placement.toLowerCase().includes('full leg')

    let sessionType: string
    if (isSleevePlacement || isLegSleevePlace) {
      sessionType = 'full_sleeve'
    } else {
      sessionType = getCoverageSession(coverage, placement)
    }

    // Map session type to size_selection for backend compatibility
    const sizeMap: Record<string, string> = {
      small: 'small',
      half_day: 'medium',
      full_day: 'large',
      full_sleeve: 'full sleeve',
    }
    const sizeSelection = sizeMap[sessionType] ?? 'medium'
    const fallbackKey = sessionType === 'full_sleeve' ? 'full_sleeve' : sessionType

    try {
      const res = await fetch(artistApiPath(artistSlug, 'intake'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_name: finalAnswers.name ?? '',
          contact: finalAnswers.contact ?? '',
          description: finalAnswers.description ?? '',
          size_selection: sizeSelection,
          placement,
          // Send coverage explicitly so crew and Telegram card have it
          coverage,
          styles: [],
          is_cover_up: false,
          cover_up_description: null,
          budget_range: '$500–$1,000',
          preferred_timing: 'flexible',
          idea_readiness: 'knows_exactly',
          reference_images: referenceImages,
          reference_image: referenceImages[0] ?? null,
          guided_discovery: null,
        }),
      })

      const data = await res.json()
      const message = data.client_message ?? ''

      const fallback = FALLBACK_PRICING[fallbackKey] ?? FALLBACK_PRICING.half_day
      const priceMin: number = typeof data.price_min === 'number' ? data.price_min : fallback.min
      const priceMax: number = typeof data.price_max === 'number' ? data.price_max : fallback.max
      const intakeId: string = data.intake_id ?? ''
      const preferredTiming: string = data.preferred_timing ?? 'flexible'

      let availableDates: string[] = []
      if (Array.isArray(data.available_dates) && data.available_dates.length > 0) {
        availableDates = data.available_dates.map((d: string) =>
          d.includes('·') ? d : d.replace(/,?\s+/, ' · ')
        )
      } else {
        availableDates = parseAvailableDates(message)
      }
      if (availableDates.length === 0) {
        availableDates = ['Thursday · May 28', 'Monday · June 1', 'Wednesday · June 3']
      }

      const estimatedDate = availableDates[0]
      setTimeout(() => {
        onComplete({
          priceMin, priceMax, estimatedDate, availableDates,
          intakeId, preferredTiming,
          summary: message || `${artistName} will review your request and confirm shortly.`,
        })
      }, 2800)

    } catch {
      const fallback = FALLBACK_PRICING[fallbackKey] ?? FALLBACK_PRICING.half_day
      setTimeout(() => {
        onComplete({
          priceMin: fallback.min, priceMax: fallback.max,
          estimatedDate: 'Thursday · May 28',
          availableDates: ['Thursday · May 28', 'Monday · June 1', 'Wednesday · June 3'],
          intakeId: '', preferredTiming: 'flexible',
          summary: `${artistName} will review your request and confirm shortly. You'll receive a message with next steps.`,
        })
      }, 2800)
    } finally {
      setLoading(false)
    }
  }

  const showInput = ['description', 'name', 'contact'].includes(step)
  const showProgress = step !== 'processing' && !loading
  const progressIndex = PROGRESS_STEPS.indexOf(step as ProgressStep)
  const progressStepNum = progressIndex >= 0 ? progressIndex + 1 : 1
  const progressLabel = progressIndex >= 0
    ? PROGRESS_LABELS[PROGRESS_STEPS[progressIndex]]
    : PROGRESS_LABELS.description

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      height: '100dvh',
      width: '100%',
      boxSizing: 'border-box',
      display: 'flex',
      flexDirection: 'column',
      background: 'var(--black)',
      maxWidth: '600px',
      margin: '0 auto',
    }}>
      {/* Header */}
      <div style={{
        padding: '14px 20px', borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', gap: '12px', flexShrink: 0,
      }}>
        <div style={{
          width: '36px', height: '36px', borderRadius: '50%', background: 'var(--gold)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontFamily: 'var(--font-display)', fontSize: '16px', color: 'var(--black)',
          fontWeight: 500, flexShrink: 0,
        }}>I</div>
        <div>
          <div style={{ fontSize: '14px', fontWeight: 500 }}>Inkbook Assistant</div>
          <div style={{ fontSize: '11px', color: 'var(--gold-dim)', display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#4CAF82', display: 'inline-block' }} />
            Booking with {artistName} · usually replies fast
          </div>
        </div>
      </div>

      {/* Progress indicator */}
      {showProgress && (
        <div style={{
          padding: '12px 20px 10px',
          borderBottom: '1px solid var(--border)',
          flexShrink: 0,
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '10px',
          }}>
            {PROGRESS_STEPS.map((s, i) => {
              const isActive = i === progressIndex
              const isCompleted = i < progressIndex
              return (
                <div
                  key={s}
                  style={{
                    width: isActive ? '8px' : '6px',
                    height: isActive ? '8px' : '6px',
                    borderRadius: '50%',
                    background: isActive || isCompleted ? 'var(--gold)' : 'transparent',
                    border: `1px solid ${isActive || isCompleted ? 'var(--gold)' : 'var(--border)'}`,
                    opacity: isCompleted ? 0.45 : 1,
                    transition: 'all 0.2s ease',
                    flexShrink: 0,
                  }}
                />
              )
            })}
          </div>
          <div style={{
            marginTop: '8px',
            textAlign: 'center',
            fontSize: '11px',
            color: 'var(--text-muted)',
            letterSpacing: '0.03em',
          }}>
            Step {progressStepNum} of 6 · {progressLabel}
          </div>
        </div>
      )}

      {/* Messages */}
      <div style={{
        flex: 1, overflowY: 'auto', padding: '16px',
        display: 'flex', flexDirection: 'column', gap: '12px',
      }}>
        {messages.map((msg, i) => (
          <div key={i}>
            <div style={{
              display: 'flex',
              justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
              alignItems: 'flex-start', gap: '8px',
            }}>
              {msg.role === 'assistant' && (
                <div style={{
                  width: '26px', height: '26px', borderRadius: '50%', background: 'var(--gold)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '12px', color: 'var(--black)', fontFamily: 'var(--font-display)',
                  fontWeight: 500, flexShrink: 0,
                }}>I</div>
              )}
              <div style={{
                maxWidth: '80%', padding: '10px 14px',
                borderRadius: msg.role === 'user' ? '18px 18px 4px 18px' : '4px 18px 18px 18px',
                background: msg.role === 'user' ? 'var(--gold)' : 'var(--surface-2)',
                color: msg.role === 'user' ? 'var(--black)' : 'var(--text)',
                fontSize: '14px', lineHeight: 1.6,
                fontWeight: msg.role === 'user' ? 500 : 300,
                border: msg.role === 'assistant' ? '1px solid var(--border)' : 'none',
              }}>
                {msg.content}
              </div>
            </div>

            {/* Chips */}
            {msg.chips && msg.stepKey && (
              <div style={{
                display: 'flex',
                flexDirection: msg.fullWidthChips ? 'column' : 'row',
                flexWrap: msg.fullWidthChips ? undefined : 'wrap',
                gap: '8px',
                marginTop: '10px',
                paddingLeft: msg.fullWidthChips ? '0' : '34px',
              }}>
                {msg.chips.map((chip, idx) => {
                  const isActive = msg.stepKey === step
                  const label = chipLabel(chip)
                  const description = chipDescription(chip)
                  const isDescriptive = description !== null
                  const isFullWidth = msg.fullWidthChips

                  return (
                    <button
                      key={idx}
                      onClick={() => handleChip(chip, msg.stepKey!)}
                      style={{
                        width: isFullWidth ? '100%' : undefined,
                        padding: isDescriptive ? '12px 18px' : '8px 16px',
                        borderRadius: isDescriptive || isFullWidth ? '10px' : '999px',
                        border: `1px solid ${isActive ? 'var(--border)' : 'rgba(201,168,76,0.07)'}`,
                        background: 'transparent',
                        color: isActive ? 'var(--text)' : 'var(--text-muted)',
                        fontSize: '13px', fontWeight: 400,
                        cursor: isActive ? 'pointer' : 'default',
                        transition: 'all 0.15s ease',
                        opacity: isActive ? 1 : 0.4,
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'flex-start',
                        gap: isDescriptive ? '3px' : 0,
                        textAlign: 'left',
                        lineHeight: 1.3,
                      }}
                      onMouseEnter={e => {
                        if (isActive) {
                          e.currentTarget.style.borderColor = 'var(--gold)'
                          e.currentTarget.style.color = 'var(--gold)'
                        }
                      }}
                      onMouseLeave={e => {
                        if (isActive) {
                          e.currentTarget.style.borderColor = 'rgba(201,168,76,0.15)'
                          e.currentTarget.style.color = 'var(--text)'
                        }
                      }}
                    >
                      <span style={{ fontWeight: isDescriptive ? 500 : 400, fontSize: '13px' }}>
                        {label}
                      </span>
                      {description && (
                        <span style={{
                          fontSize: '11px', color: 'var(--text-muted)',
                          fontWeight: 300, letterSpacing: '0.02em',
                        }}>
                          {description}
                        </span>
                      )}
                    </button>
                  )
                })}
              </div>
            )}

            {/* Upload zone */}
            {msg.isUpload && step === 'reference' && !uploadDone && (
              <div style={{ paddingLeft: '34px', marginTop: '10px' }}>
                <input ref={fileRef} type="file" accept="image/*"
                  style={{ display: 'none' }} onChange={handleImageUpload} />

                {referenceImages.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '10px' }}>
                    {referenceImages.map((src, idx) => (
                      <div key={idx} style={{ position: 'relative' }}>
                        <img src={src} alt={`Reference ${idx + 1}`} style={{
                          width: '72px', height: '72px', objectFit: 'cover',
                          borderRadius: '8px', border: '1px solid var(--gold)',
                        }} />
                        <button
                          onClick={() => setReferenceImages(prev => prev.filter((_, i) => i !== idx))}
                          style={{
                            position: 'absolute', top: '-6px', right: '-6px',
                            width: '18px', height: '18px', borderRadius: '50%',
                            background: 'var(--surface-2)', border: '1px solid var(--border)',
                            color: 'var(--text-muted)', fontSize: '10px', cursor: 'pointer',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                          }}
                        >✕</button>
                      </div>
                    ))}
                  </div>
                )}

                {referenceImages.length < MAX_IMAGES && (
                  <div onClick={() => fileRef.current?.click()} style={{
                    border: '1px dashed var(--gold)', borderRadius: '8px',
                    padding: referenceImages.length > 0 ? '12px 16px' : '20px 16px',
                    textAlign: 'center', cursor: 'pointer',
                    maxWidth: '280px', marginBottom: '10px',
                    background: 'rgba(201,168,76,0.04)', transition: 'all 0.15s ease',
                  }}
                    onMouseEnter={e => { e.currentTarget.style.background = 'rgba(201,168,76,0.09)' }}
                    onMouseLeave={e => { e.currentTarget.style.background = 'rgba(201,168,76,0.04)' }}
                  >
                    {referenceImages.length === 0 ? (
                      <>
                        <div style={{ fontSize: '18px', marginBottom: '6px' }}>↑</div>
                        <div style={{ color: 'var(--gold)', fontSize: '13px', fontWeight: 500, marginBottom: '3px' }}>
                          Tap to upload a reference image
                        </div>
                        <div style={{ color: 'var(--text-muted)', fontSize: '11px' }}>
                          JPG, PNG, or HEIC · Up to {MAX_IMAGES} images
                        </div>
                      </>
                    ) : (
                      <div style={{ color: 'var(--gold)', fontSize: '13px', fontWeight: 500 }}>
                        + Add another ({referenceImages.length}/{MAX_IMAGES})
                      </div>
                    )}
                  </div>
                )}

                <div style={{ display: 'flex', gap: '8px' }}>
                  {referenceImages.length > 0 && (
                    <button onClick={handleUploadDone} style={{
                      padding: '8px 20px', background: 'var(--gold)', color: 'var(--black)',
                      borderRadius: '8px', fontSize: '13px', fontWeight: 600,
                      border: 'none', cursor: 'pointer',
                    }}>Done</button>
                  )}
                  <button onClick={handleUploadDone} style={{
                    padding: '8px 14px', background: 'none', color: 'var(--text-muted)',
                    borderRadius: '8px', fontSize: '12px', fontWeight: 400,
                    border: '1px solid var(--border)', cursor: 'pointer',
                  }}>
                    {referenceImages.length > 0 ? 'Skip remaining' : 'Skip for now'}
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div style={{ display: 'flex', gap: '6px', paddingLeft: '34px' }}>
            {[0, 1, 2].map(i => (
              <div key={i} style={{
                width: '7px', height: '7px', borderRadius: '50%', background: 'var(--gold-dim)',
                animation: 'pulse 1.2s ease-in-out infinite',
                animationDelay: `${i * 0.2}s`,
              }} />
            ))}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      {showInput && (
        <div style={{
          padding: '12px 16px',
          paddingBottom: 'calc(12px + env(safe-area-inset-bottom))',
          borderTop: '1px solid var(--border)',
          display: 'flex', gap: '8px', flexShrink: 0,
        }}>
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onFocus={() => {
              setTimeout(
                () => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }),
                300
              )
            }}
            onKeyDown={e => e.key === 'Enter' && handleSend()}
            placeholder={
              step === 'name' ? 'Your name...' :
              step === 'contact' ? 'Your phone number...' :
              'Describe your tattoo idea...'
            }
            style={{
              flex: 1, background: 'var(--surface-2)', border: '1px solid var(--border)',
              borderRadius: '8px', padding: '11px 14px', color: 'var(--text)',
              fontSize: '14px', outline: 'none',
            }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim()}
            style={{
              padding: '11px 18px',
              background: input.trim() ? 'var(--gold)' : 'var(--surface-2)',
              color: input.trim() ? 'var(--black)' : 'var(--text-muted)',
              borderRadius: '8px', fontSize: '13px', fontWeight: 600,
              border: '1px solid var(--border)', transition: 'all 0.15s ease', cursor: 'pointer',
            }}
          >
            Send
          </button>
        </div>
      )}

      <style>{`
        * { -webkit-tap-highlight-color: transparent; }
        input { font-size: 16px !important; }
        @keyframes pulse {
          0%, 100% { opacity: 0.3; transform: scale(0.8); }
          50% { opacity: 1; transform: scale(1); }
        }
      `}</style>
    </div>
  )
}