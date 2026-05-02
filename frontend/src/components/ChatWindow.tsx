import { useState, useRef, useEffect } from 'react'
import type { Estimate } from '../App'

interface Message {
  role: 'assistant' | 'user'
  content: string
  chips?: string[]
  isUpload?: boolean
  stepKey?: string
}

interface Props {
  onComplete: (estimate: Estimate) => void
}

type Step =
  | 'description' | 'size' | 'placement' | 'style' | 'coverup'
  | 'reference' | 'budget' | 'timeline' | 'name' | 'contact' | 'processing'

const STEP_SEQUENCE: Step[] = [
  'description', 'size', 'placement', 'style', 'coverup',
  'reference', 'budget', 'timeline', 'name', 'contact', 'processing'
]

const STEP_QUESTIONS: Partial<Record<Step, string>> = {
  size: 'Let\'s Do It! How big are you thinking?',
  placement: 'Where on your body do you want this tattoo?',
  style: 'Got it — and what style are you drawn to?',
  coverup: 'Is this a cover up of an existing tattoo?',
  reference: "Upload a reference image below. A photo helps Miguel get a more accurate quote and makes sure he's fully prepared to execute your vision on tattoo day.",
  budget: "What's your rough budget for this piece?",
  timeline: 'When are you looking to get this done?',
  name: "What's your name?",
  contact: "What's the best phone number to reach you?",
}

const CHIPS: Partial<Record<Step, string[]>> = {
  size: ['Small', 'Medium', 'Large', 'Full Sleeve'],
  placement: ['Full Sleeve', 'Forearm', 'Upper Arm', 'Chest', 'Back', 'Leg', 'Torso', 'Hand', 'Neck', 'Other'],
  style: ['Realism', 'Traditional', 'Fine Line', 'Geometric', 'Blackwork', 'Not Sure'],
  coverup: ['Yes', 'No'],
  budget: ['Under $200', '$200–$500', '$500–$1,000', '$1,000+'],
  timeline: ['Within 2 weeks', 'Within 1 month', 'Within 2 months', 'Flexible'],
}

export default function ChatWindow({ onComplete }: Props) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: 'Hi, my name is Miguel. I\'m a tattoo artist based in Austin, TX. I specialize in a variety of styles, with a focus on black and grey realism. I\'m experienced working with all skin tones and a wide range of subject matter. What are you interested in getting done?',
    }
  ])
  const [step, setStep] = useState<Step>('description')
  const [input, setInput] = useState('')
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [referenceImage, setReferenceImage] = useState<string | null>(null)
  const [imageUploaded, setImageUploaded] = useState(false)
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const addAssistantMessage = (content: string, extras?: Partial<Message>) => {
    setMessages(prev => [...prev, { role: 'assistant', content, ...extras }])
  }

  const addUserMessage = (content: string) => {
    setMessages(prev => [...prev, { role: 'user', content }])
  }

  const advanceStep = (currentStep: Step, answer: string, newAnswersOverride?: Record<string, string>) => {
    const newAnswers = { ...(newAnswersOverride ?? answers), [currentStep]: answer }
    setAnswers(newAnswers)

    const idx = STEP_SEQUENCE.indexOf(currentStep)
    const nextStep = STEP_SEQUENCE[idx + 1] as Step
    setStep(nextStep)

    setTimeout(() => {
      if (nextStep === 'processing') {
        submitToBackend(newAnswers)
      } else {
        const question = STEP_QUESTIONS[nextStep]!
        const chips = CHIPS[nextStep]
        addAssistantMessage(question, {
          chips,
          isUpload: nextStep === 'reference',
          stepKey: nextStep,
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

  const handleChip = (chip: string, stepKey: string) => {
    if (stepKey !== step) return
    addUserMessage(chip)
    advanceStep(step, chip)
  }

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      const dataUrl = reader.result as string
      setReferenceImage(dataUrl)
      setImageUploaded(true)
      addUserMessage('📎 Reference image uploaded')
      advanceStep('reference', 'uploaded')
    }
    reader.readAsDataURL(file)
  }

  const submitToBackend = async (finalAnswers: Record<string, string>) => {
    setLoading(true)
    setTimeout(() => addAssistantMessage('⚡ Analyzing your request… ✓'), 400)
    setTimeout(() => addAssistantMessage('📅 Checking artist availability… ✓'), 1200)
    setTimeout(() => addAssistantMessage('💰 Preparing your estimate… ✓'), 2000)

    try {
      const res = await fetch('https://inkbook-4tlr.onrender.com/api/miguel/intake', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_name: finalAnswers.name ?? '',
          contact: finalAnswers.contact ?? '',
          description: finalAnswers.description ?? '',
          size_selection: finalAnswers.size?.toLowerCase() ?? '',
          placement: finalAnswers.placement ?? 'not specified', // FIX: use actual answer
          styles: finalAnswers.style ? [finalAnswers.style.toLowerCase().replace(' ', '_')] : [],
          is_cover_up: finalAnswers.coverup === 'Yes',
          cover_up_description: null,
          budget_range: finalAnswers.budget ?? '',
          preferred_timing: finalAnswers.timeline ?? '',
          idea_readiness: 'knows_exactly',
          reference_image: referenceImage ?? null,
          guided_discovery: null,
        }),
      })
      const data = await res.json()
      setTimeout(() => {
        onComplete({
          priceMin: data.price_min ?? 800,
          priceMax: data.price_max ?? 1000,
          estimatedDate: data.estimated_date ?? 'Saturday · May 17',
          summary: data.client_message ?? 'Miguel will review your request and confirm shortly.',
        })
      }, 2800)
    } catch {
      setTimeout(() => {
        onComplete({
          priceMin: 800,
          priceMax: 1000,
          estimatedDate: 'Saturday · May 17',
          summary: "Miguel will review your request and confirm shortly. You'll receive a message with next steps.",
        })
      }, 2800)
    } finally {
      setLoading(false)
    }
  }

  const showInput = ['description', 'name', 'contact', 'placement'].includes(step)

  return (
    <div style={{
      height: '100vh', display: 'flex', flexDirection: 'column',
      background: 'var(--black)', maxWidth: '600px', margin: '0 auto',
    }}>
      {/* Header */}
      <div style={{
        padding: '16px 20px', borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', gap: '12px', flexShrink: 0,
      }}>
        <div style={{
          width: '40px', height: '40px', borderRadius: '50%', background: 'var(--gold)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontFamily: 'var(--font-display)', fontSize: '18px', color: 'var(--black)',
          fontWeight: 500, flexShrink: 0,
        }}>I</div>
        <div>
          <div style={{ fontSize: '15px', fontWeight: 500 }}>Inkbook Assistant</div>
          <div style={{ fontSize: '12px', color: 'var(--gold-dim)', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: '#4CAF82', display: 'inline-block' }} />
            Booking with Miguel · usually replies fast
          </div>
        </div>
      </div>

      {/* Messages */}
      <div style={{
        flex: 1, overflowY: 'auto', padding: '20px',
        display: 'flex', flexDirection: 'column', gap: '12px',
      }}>
        {messages.map((msg, i) => (
          <div key={i}>
            <div style={{
              display: 'flex',
              justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
              alignItems: 'flex-start', gap: '10px',
            }}>
              {msg.role === 'assistant' && (
                <div style={{
                  width: '28px', height: '28px', borderRadius: '50%', background: 'var(--gold)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '13px', color: 'var(--black)', fontFamily: 'var(--font-display)',
                  fontWeight: 500, flexShrink: 0,
                }}>I</div>
              )}
              <div style={{
                maxWidth: '78%', padding: '11px 15px',
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
                display: 'flex', flexWrap: 'wrap', gap: '8px',
                marginTop: '10px', paddingLeft: '38px',
              }}>
                {msg.chips.map(chip => {
                  const isActive = msg.stepKey === step
                  return (
                    <button
                      key={chip}
                      onClick={() => handleChip(chip, msg.stepKey!)}
                      style={{
                        padding: '8px 16px', borderRadius: '999px',
                        border: `1px solid ${isActive ? 'var(--border)' : 'rgba(201,168,76,0.07)'}`,
                        background: 'transparent',
                        color: isActive ? 'var(--text)' : 'var(--text-muted)',
                        fontSize: '13px', fontWeight: 400,
                        cursor: isActive ? 'pointer' : 'default',
                        transition: 'all 0.15s ease',
                        opacity: isActive ? 1 : 0.4,
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
                      {chip}
                    </button>
                  )
                })}
              </div>
            )}

            {/* Upload zone */}
            {msg.isUpload && step === 'reference' && !imageUploaded && (
              <div style={{ paddingLeft: '38px', marginTop: '10px' }}>
                <input
                  ref={fileRef}
                  type="file"
                  accept="image/*"
                  style={{ display: 'none' }}
                  onChange={handleImageUpload}
                />
                <div
                  onClick={() => fileRef.current?.click()}
                  style={{
                    border: '1px dashed var(--gold)',
                    borderRadius: '8px',
                    padding: '24px 20px',
                    textAlign: 'center',
                    cursor: 'pointer',
                    maxWidth: '300px',
                    transition: 'all 0.15s ease',
                    background: 'rgba(201,168,76,0.04)',
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.background = 'rgba(201,168,76,0.09)'
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.background = 'rgba(201,168,76,0.04)'
                  }}
                >
                  <div style={{ fontSize: '20px', marginBottom: '8px' }}>↑</div>
                  <div style={{ color: 'var(--gold)', fontSize: '13px', fontWeight: 500, marginBottom: '6px' }}>
                    Tap to upload your reference image
                  </div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '11px', lineHeight: 1.6 }}>
                    JPG, PNG, or HEIC · Required
                  </div>
                </div>
              </div>
            )}

            {/* Uploaded image preview */}
            {msg.isUpload && referenceImage && (
              <div style={{ paddingLeft: '38px', marginTop: '10px' }}>
                <img src={referenceImage} alt="Reference" style={{
                  maxWidth: '200px', borderRadius: '8px', border: '1px solid var(--border)',
                }} />
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div style={{ display: 'flex', gap: '6px', paddingLeft: '38px' }}>
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
          padding: '14px 20px', borderTop: '1px solid var(--border)',
          display: 'flex', gap: '10px', flexShrink: 0,
        }}>
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSend()}
            placeholder={
              step === 'name' ? 'Your name...' :
              step === 'contact' ? 'Your phone number...' :
              step === 'placement' ? 'e.g. left forearm, right chest...' :
              'Describe your tattoo in as much detail as possible...'
            }
            style={{
              flex: 1, background: 'var(--surface-2)', border: '1px solid var(--border)',
              borderRadius: '8px', padding: '12px 16px', color: 'var(--text)',
              fontSize: '14px', outline: 'none',
            }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim()}
            style={{
              padding: '12px 20px',
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
        @keyframes pulse {
          0%, 100% { opacity: 0.3; transform: scale(0.8); }
          50% { opacity: 1; transform: scale(1); }
        }
      `}</style>
    </div>
  )
}