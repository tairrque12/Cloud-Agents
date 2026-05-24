import {
  useMemo,
  useState,
  type ChangeEvent,
  type CSSProperties,
  type FocusEvent,
  type FormEvent,
  type ReactNode,
} from 'react'
import {
  API_PRICING_LABELS,
  DEFAULT_API_PRICING,
  SCHEDULING_TOOL_OPTIONS,
  SPECIALTY_OPTIONS,
  type ApiPricingConfig,
} from '../types/artist'

const NETLIFY_FORM_NAME = 'artist-onboarding'

type Step =
  | 'identity'
  | 'studio'
  | 'rates'
  | 'scheduling'
  | 'contact'
  | 'review'
  | 'success'

const FLOW_STEPS: Exclude<Step, 'success'>[] = [
  'identity',
  'studio',
  'rates',
  'scheduling',
  'contact',
  'review',
]

const STEP_META: Record<Exclude<Step, 'success'>, { title: string; helper: string }> = {
  identity: {
    title: 'Your identity',
    helper:
      'This is how clients will identify you. We assign your personal booking link after we review your application.',
  },
  studio: {
    title: 'Your studio',
    helper:
      'Your AI agent introduces itself to every client using your bio and specialties. The more specific you are, the better it represents your style and filters out the wrong clients.',
  },
  rates: {
    title: 'Your rates',
    helper:
      "These numbers power your agent's estimates. It will never give clients a final price — it quotes a range and makes clear that you approve every booking before anything is confirmed.",
  },
  scheduling: {
    title: 'Your scheduling',
    helper:
      'Your agent will only suggest dates that match your actual schedule. We handle the technical connection — you just tell us what you use and we take it from there.',
  },
  contact: {
    title: 'Your contact',
    helper:
      'This is how we reach you during setup. Your agent will be configured and tested before your link goes live.',
  },
  review: {
    title: 'Review and submit',
    helper:
      "Take a moment to review your details. Once you submit, we'll start building your booking agent. You'll hear from us within 24 hours.",
  },
}

const US_STATES = [
  'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
  'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
  'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
  'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
  'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
  'DC',
]

function buildNetlifyFormBody(fields: Record<string, string>): string {
  const params = new URLSearchParams()
  params.set('form-name', NETLIFY_FORM_NAME)
  for (const [key, value] of Object.entries(fields)) {
    params.set(key, value)
  }
  return params.toString()
}

export default function ArtistOnboarding() {
  const [step, setStep] = useState<Step>('identity')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const [name, setName] = useState('')
  const [profilePhotoUrl, setProfilePhotoUrl] = useState<string | null>(null)
  const [profilePhotoName, setProfilePhotoName] = useState('')

  const [studioName, setStudioName] = useState('')
  const [city, setCity] = useState('')
  const [state, setState] = useState('')
  const [bio, setBio] = useState('')
  const [specialties, setSpecialties] = useState<string[]>([])

  const [pricing, setPricing] = useState<ApiPricingConfig>({ ...DEFAULT_API_PRICING })

  const [phoneNumber, setPhoneNumber] = useState('')
  const [schedulingTool, setSchedulingTool] = useState('')
  const [schedulingToolOther, setSchedulingToolOther] = useState('')

  const [email, setEmail] = useState('')
  const [instagramHandle, setInstagramHandle] = useState('')
  const [notes, setNotes] = useState('')

  const stepIndex = FLOW_STEPS.indexOf(step as Exclude<Step, 'success'>)
  const progress =
    step === 'success' ? 100 : ((stepIndex + 1) / FLOW_STEPS.length) * 100

  const inputStyle = (): CSSProperties => ({
    background: 'rgba(255,255,255,0.03)',
    border: '1px solid rgba(201,168,76,0.15)',
    color: 'var(--text)',
    padding: '14px 18px',
    fontSize: '16px',
    borderRadius: '2px',
    outline: 'none',
    width: '100%',
    boxSizing: 'border-box',
  })

  const focusHandlers = {
    onFocus: (e: FocusEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
      e.currentTarget.style.borderColor = 'rgba(201,168,76,0.45)'
    },
    onBlur: (e: FocusEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
      e.currentTarget.style.borderColor = 'rgba(201,168,76,0.15)'
    },
  }

  const toggleSpecialty = (value: string) => {
    setSpecialties((prev) =>
      prev.includes(value) ? prev.filter((s) => s !== value) : [...prev, value]
    )
  }

  const handlePhotoChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) {
      setProfilePhotoUrl(null)
      setProfilePhotoName('')
      return
    }
    if (file.size > 2 * 1024 * 1024) {
      setError('Profile photo must be under 2 MB.')
      e.target.value = ''
      return
    }
    const reader = new FileReader()
    reader.onload = () => {
      setProfilePhotoUrl(typeof reader.result === 'string' ? reader.result : null)
      setProfilePhotoName(file.name)
      setError('')
    }
    reader.readAsDataURL(file)
  }

  const validateIdentity = () => {
    if (!name.trim()) {
      setError('Full name is required.')
      return false
    }
    setError('')
    return true
  }

  const validateStudio = () => {
    if (!city.trim() || !state) {
      setError('City and state are required.')
      return false
    }
    if (!bio.trim()) {
      setError('A short bio is required.')
      return false
    }
    if (bio.length > 300) {
      setError('Bio must be 300 characters or fewer.')
      return false
    }
    setError('')
    return true
  }

  const validateScheduling = () => {
    if (!phoneNumber.trim()) {
      setError('Phone number is required.')
      return false
    }
    if (!schedulingTool) {
      setError('Select how you track appointments.')
      return false
    }
    if (schedulingTool === 'Other' && !schedulingToolOther.trim()) {
      setError('Tell us which scheduling tool you use.')
      return false
    }
    setError('')
    return true
  }

  const validateContact = () => {
    if (!email.trim() || !email.includes('@')) {
      setError('A valid email address is required.')
      return false
    }
    setError('')
    return true
  }

  const handleSubmit = async () => {
    if (
      !validateIdentity() ||
      !validateStudio() ||
      !validateScheduling() ||
      !validateContact()
    ) {
      if (!name.trim()) setStep('identity')
      else if (!city.trim() || !state || !bio.trim()) setStep('studio')
      else if (!phoneNumber.trim() || !schedulingTool) setStep('scheduling')
      else setStep('contact')
      return
    }

    if (import.meta.env.DEV) {
      setError(
        'Applications submit through Netlify Forms on the deployed site. Open your Netlify URL or production domain to test submission.'
      )
      return
    }

    setSubmitting(true)
    setError('')
    try {
      const body = buildNetlifyFormBody({
        name: name.trim(),
        profile_photo_url: profilePhotoUrl ?? '',
        studio_name: studioName.trim(),
        city: city.trim(),
        state,
        bio: bio.trim(),
        specialties: specialties.map((s) => s.toLowerCase()).join(', '),
        pricing_json: JSON.stringify(pricing),
        phone_number: phoneNumber.trim(),
        scheduling_tool: schedulingTool,
        scheduling_tool_other:
          schedulingTool === 'Other' ? schedulingToolOther.trim() : '',
        email: email.trim(),
        instagram_handle: instagramHandle.trim(),
        notes: notes.trim(),
      })

      const res = await fetch('/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body,
      })

      if (!res.ok) {
        throw new Error('Could not submit your application. Please try again.')
      }

      setStep('success')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleFormSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (step === 'review') {
      void handleSubmit()
    }
  }

  const summaryRows = useMemo(
    () => [
      { label: 'Name', value: name.trim() },
      { label: 'Profile photo', value: profilePhotoName || 'Not provided' },
      { label: 'Studio', value: studioName.trim() || '—' },
      { label: 'Location', value: `${city.trim()}, ${state}` },
      { label: 'Bio', value: bio.trim() },
      { label: 'Specialties', value: specialties.join(', ') || '—' },
      { label: 'Phone', value: phoneNumber.trim() },
      {
        label: 'Scheduling',
        value:
          schedulingTool === 'Other'
            ? schedulingToolOther.trim() || 'Other'
            : schedulingTool,
      },
      { label: 'Email', value: email.trim() },
      { label: 'Instagram', value: instagramHandle.trim() || '—' },
      { label: 'Setup notes', value: notes.trim() || '—' },
    ],
    [
      name,
      profilePhotoName,
      studioName,
      city,
      state,
      bio,
      specialties,
      phoneNumber,
      schedulingTool,
      schedulingToolOther,
      email,
      instagramHandle,
      notes,
    ]
  )

  return (
    <PageShell>
      <form
        name={NETLIFY_FORM_NAME}
        method="POST"
        data-netlify="true"
        netlify=""
        onSubmit={handleFormSubmit}
        style={{ width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center' }}
      >
        <input type="hidden" name="form-name" value={NETLIFY_FORM_NAME} />
      <header style={{ width: '100%', maxWidth: 640, marginBottom: 32 }}>
        <p style={{ color: 'var(--gold)', letterSpacing: '0.2em', fontSize: 11, marginBottom: 12 }}>
          INKBOOK FOR ARTISTS
        </p>
        <h1 style={{
          fontFamily: 'var(--font-display)',
          fontSize: 'clamp(2rem, 5vw, 2.75rem)',
          fontWeight: 300,
          marginBottom: 12,
        }}>
          Apply for your booking agent
        </h1>
        <p style={{ color: 'var(--text-muted)', lineHeight: 1.6 }}>
          Tell us about your work — we&apos;ll configure your AI booking agent and send your link within 24 hours.
        </p>
      </header>

      {step !== 'success' && (
        <StepProgress stepIndex={stepIndex} progress={progress} step={step} />
      )}

      {error && (
        <p style={{
          color: '#e07070',
          marginBottom: 16,
          maxWidth: 640,
          width: '100%',
          textAlign: 'left',
        }}>
          {error}
        </p>
      )}

      {step === 'identity' && (
        <FormSection meta={STEP_META.identity}>
          <Field label="Full name">
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Alex Rivera"
              style={inputStyle()}
              {...focusHandlers}
            />
          </Field>
          <Field label="Profile photo (optional)">
            <input
              type="file"
              accept="image/*"
              onChange={handlePhotoChange}
              style={{ ...inputStyle(), padding: 12 }}
            />
            {profilePhotoName && (
              <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>
                Selected: {profilePhotoName}
              </p>
            )}
          </Field>
          <NavRow onNext={() => validateIdentity() && setStep('studio')} />
        </FormSection>
      )}

      {step === 'studio' && (
        <FormSection meta={STEP_META.studio}>
          <Field label="Studio name (optional)">
            <input
              value={studioName}
              onChange={(e) => setStudioName(e.target.value)}
              placeholder="Independent / Studio name"
              style={inputStyle()}
              {...focusHandlers}
            />
          </Field>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 120px', gap: 12 }}>
            <Field label="City">
              <input
                value={city}
                onChange={(e) => setCity(e.target.value)}
                placeholder="Austin"
                style={inputStyle()}
                {...focusHandlers}
              />
            </Field>
            <Field label="State">
              <select
                value={state}
                onChange={(e) => setState(e.target.value)}
                style={inputStyle()}
                {...focusHandlers}
              >
                <option value="">—</option>
                {US_STATES.map((st) => (
                  <option key={st} value={st}>{st}</option>
                ))}
              </select>
            </Field>
          </div>
          <Field label="Short bio">
            <textarea
              value={bio}
              onChange={(e) => setBio(e.target.value.slice(0, 300))}
              placeholder="Black and grey realism in Austin — custom pieces, cover-ups welcome."
              rows={4}
              style={{ ...inputStyle(), resize: 'vertical' }}
              {...focusHandlers}
            />
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6, textAlign: 'right' }}>
              {bio.length}/300
            </p>
          </Field>
          <Field label="Specialties">
            <TagRow>
              {SPECIALTY_OPTIONS.map((option) => {
                const active = specialties.includes(option)
                return (
                  <button
                    key={option}
                    type="button"
                    onClick={() => toggleSpecialty(option)}
                    style={{
                      padding: '8px 14px',
                      borderRadius: 999,
                      border: active ? '1px solid var(--gold)' : '1px solid rgba(201,168,76,0.2)',
                      background: active ? 'rgba(201,168,76,0.12)' : 'transparent',
                      color: active ? 'var(--gold)' : 'var(--text-muted)',
                      fontSize: 13,
                    }}
                  >
                    {option}
                  </button>
                )
              })}
            </TagRow>
          </Field>
          <NavRow
            onBack={() => setStep('identity')}
            onNext={() => validateStudio() && setStep('rates')}
          />
        </FormSection>
      )}

      {step === 'rates' && (
        <FormSection meta={STEP_META.rates}>
          {(Object.keys(pricing) as (keyof ApiPricingConfig)[]).map((tier) => (
            <PricingTierCard key={tier}>
              <p style={{ marginBottom: 12, color: 'var(--gold)' }}>{API_PRICING_LABELS[tier]}</p>
              <PricingFields>
                {(['min', 'max', 'deposit'] as const).map((field) => (
                  <Field key={field} label={field === 'min' ? 'Min $' : field === 'max' ? 'Max $' : 'Deposit $'}>
                    <input
                      type="number"
                      min={0}
                      value={pricing[tier][field]}
                      onChange={(e) => {
                        const value = Number(e.target.value) || 0
                        setPricing((prev) => ({
                          ...prev,
                          [tier]: { ...prev[tier], [field]: value },
                        }))
                      }}
                      style={inputStyle()}
                      {...focusHandlers}
                    />
                  </Field>
                ))}
              </PricingFields>
            </PricingTierCard>
          ))}
          <NavRow onBack={() => setStep('studio')} onNext={() => setStep('scheduling')} />
        </FormSection>
      )}

      {step === 'scheduling' && (
        <FormSection meta={STEP_META.scheduling}>
          <Field label="Phone number">
            <input
              type="tel"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              placeholder="(512) 555-0100"
              style={inputStyle()}
              {...focusHandlers}
            />
            <HelperSubtext>
              We&apos;ll text or call you during setup to walk through your calendar connection
              and make sure your agent has accurate availability.
            </HelperSubtext>
          </Field>
          <Field label="How do you currently track your appointments?">
            <select
              value={schedulingTool}
              onChange={(e) => setSchedulingTool(e.target.value)}
              style={inputStyle()}
              {...focusHandlers}
            >
              <option value="">Select one…</option>
              {SCHEDULING_TOOL_OPTIONS.map((option) => (
                <option key={option} value={option}>{option}</option>
              ))}
            </select>
            <HelperSubtext>
              This tells us how to connect your agent to your real schedule. We&apos;ll reach out
              to walk you through the setup based on what you use.
            </HelperSubtext>
          </Field>
          {schedulingTool === 'Other' && (
            <Field label="Which tool do you use?">
              <input
                value={schedulingToolOther}
                onChange={(e) => setSchedulingToolOther(e.target.value)}
                placeholder="e.g. Calendly, pen and paper at the shop…"
                style={inputStyle()}
                {...focusHandlers}
              />
            </Field>
          )}
          <NavRow
            onBack={() => setStep('rates')}
            onNext={() => validateScheduling() && setStep('contact')}
          />
        </FormSection>
      )}

      {step === 'contact' && (
        <FormSection meta={STEP_META.contact}>
          <Field label="Email address">
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@email.com"
              style={inputStyle()}
              {...focusHandlers}
            />
            <HelperSubtext>
              We&apos;ll send your booking page link here once your agent is configured. Usually within 24 hours.
            </HelperSubtext>
          </Field>
          <Field label="Instagram handle (optional)">
            <input
              value={instagramHandle}
              onChange={(e) => setInstagramHandle(e.target.value)}
              placeholder="@yourhandle"
              style={inputStyle()}
              {...focusHandlers}
            />
            <HelperSubtext>
              Helps us personalize your agent&apos;s intro and verify your profile.
            </HelperSubtext>
          </Field>
          <Field label="Any notes for setup (optional)">
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Things you don't tattoo, how you prefer to communicate with clients…"
              rows={4}
              style={{ ...inputStyle(), resize: 'vertical' }}
              {...focusHandlers}
            />
            <HelperSubtext>
              Anything specific about how you work with clients that your agent should know.
            </HelperSubtext>
          </Field>
          <NavRow
            onBack={() => setStep('scheduling')}
            onNext={() => validateContact() && setStep('review')}
          />
        </FormSection>
      )}

      {step === 'review' && (
        <FormSection meta={STEP_META.review}>
          <div style={{
            border: '1px solid rgba(201,168,76,0.15)',
            borderRadius: 4,
            overflow: 'hidden',
            marginBottom: 8,
          }}>
            {summaryRows.map(({ label, value }) => (
              <div
                key={label}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '140px 1fr',
                  gap: 12,
                  padding: '12px 16px',
                  borderBottom: '1px solid rgba(201,168,76,0.08)',
                  fontSize: 14,
                }}
              >
                <span style={{ color: 'var(--text-muted)' }}>{label}</span>
                <span style={{ color: 'var(--text)', wordBreak: 'break-word' }}>{value}</span>
              </div>
            ))}
            <PricingSummary pricing={pricing} />
          </div>
          <NavRow
            onBack={() => setStep('contact')}
            onNext={handleSubmit}
            nextLabel={submitting ? 'Submitting…' : 'Submit my application'}
            nextDisabled={submitting}
          />
        </FormSection>
      )}

      {step === 'success' && (
        <FormSection meta={{
          title: "You're in.",
          helper:
            "We have everything we need to build your booking agent. Check your email within 24 hours — we'll send your personal booking link once everything is live and tested.",
        }}>
          <div style={{
            border: '1px solid rgba(201,168,76,0.25)',
            borderRadius: 4,
            padding: 24,
            background: 'rgba(201,168,76,0.06)',
            textAlign: 'center',
          }}>
            <p style={{ color: 'var(--text-muted)', lineHeight: 1.7, fontSize: 15 }}>
              Our team is reviewing your application now. No action needed on your end — we&apos;ll reach out at {email.trim() || 'the email you provided'}.
            </p>
          </div>
        </FormSection>
      )}
      </form>
    </PageShell>
  )
}

function StepProgress({
  stepIndex,
  progress,
  step,
}: {
  stepIndex: number
  progress: number
  step: Step
}) {
  return (
    <div style={{ width: '100%', maxWidth: 640, marginBottom: 28 }}>
      <ProgressFill progress={progress} />
      <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
        Step {stepIndex + 1} of {FLOW_STEPS.length} · {STEP_META[step as Exclude<Step, 'success'>].title}
      </p>
    </div>
  )
}

function ProgressFill({ progress }: { progress: number }) {
  return (
    <div style={{
      height: 3,
      background: 'rgba(201,168,76,0.12)',
      borderRadius: 999,
      overflow: 'hidden',
      marginBottom: 12,
    }}>
      <div style={{
        height: '100%',
        width: `${progress}%`,
        background: 'var(--gold)',
        transition: 'width 0.25s ease',
      }} />
    </div>
  )
}

function TagRow({ children }: { children: ReactNode }) {
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
      {children}
    </div>
  )
}

function PricingTierCard({ children }: { children: ReactNode }) {
  return (
    <div style={{
      border: '1px solid rgba(201,168,76,0.12)',
      borderRadius: 4,
      padding: 16,
      marginBottom: 12,
    }}>
      {children}
    </div>
  )
}

function PricingFields({ children }: { children: ReactNode }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
      {children}
    </div>
  )
}

function PricingSummary({ pricing }: { pricing: ApiPricingConfig }) {
  return (
    <div style={{ padding: '16px', background: 'rgba(255,255,255,0.02)' }}>
      <p style={{ color: 'var(--gold)', marginBottom: 12, fontSize: 14 }}>Pricing</p>
      {(Object.keys(pricing) as (keyof ApiPricingConfig)[]).map((tier) => (
        <p key={tier} style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 6 }}>
          {API_PRICING_LABELS[tier]}: ${pricing[tier].min}–${pricing[tier].max} (deposit ${pricing[tier].deposit})
        </p>
      ))}
    </div>
  )
}

function PageShell({ children }: { children: ReactNode }) {
  return (
    <div style={{
      background: 'var(--black)',
      minHeight: '100vh',
      width: '100%',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      padding: '80px 24px 120px',
      color: 'var(--text)',
      boxSizing: 'border-box',
    }}>
      {children}
    </div>
  )
}

function FormSection({
  meta,
  children,
}: {
  meta: { title: string; helper: string }
  children: ReactNode
}) {
  return (
    <section style={{ width: '100%', maxWidth: 640, textAlign: 'left' }}>
      <h2 style={{
        fontFamily: 'var(--font-display)',
        fontSize: '1.75rem',
        fontWeight: 400,
        marginBottom: 10,
      }}>
        {meta.title}
      </h2>
      <p style={{
        color: 'var(--text-muted)',
        fontSize: 14,
        lineHeight: 1.65,
        marginBottom: 24,
      }}>
        {meta.helper}
      </p>
      {children}
    </section>
  )
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label style={{ display: 'block', marginBottom: 16 }}>
      <span style={{ display: 'block', marginBottom: 8, fontSize: 13, color: 'var(--text-muted)' }}>
        {label}
      </span>
      {children}
    </label>
  )
}

function HelperSubtext({ children }: { children: ReactNode }) {
  return (
    <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8, lineHeight: 1.55 }}>
      {children}
    </p>
  )
}

function NavRow({
  onBack,
  onNext,
  nextLabel = 'Continue',
  nextDisabled = false,
}: {
  onBack?: () => void
  onNext: () => void
  nextLabel?: string
  nextDisabled?: boolean
}) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 28, gap: 12 }}>
      {onBack ? (
        <button type="button" onClick={onBack} style={{ color: 'var(--text-muted)', padding: '12px 0' }}>
          Back
        </button>
      ) : <span />}
      <button
        type="button"
        disabled={nextDisabled}
        onClick={onNext}
        style={{
          padding: '14px 28px',
          background: nextDisabled ? 'rgba(201,168,76,0.35)' : 'var(--gold)',
          color: 'var(--black)',
          borderRadius: 2,
          fontWeight: 500,
          opacity: nextDisabled ? 0.7 : 1,
        }}
      >
        {nextLabel}
      </button>
    </div>
  )
}
