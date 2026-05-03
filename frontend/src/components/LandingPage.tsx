// src/components/LandingPage.tsx
// Inkbook — Landing Page
// Angle: "Booking with Miguel is easy"
// Sells simplicity — no DMs, no waiting, instant estimate, real dates

interface Props {
  onStart: () => void
}

export default function LandingPage({ onStart }: Props) {
  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '60px 24px 48px',
      background: 'var(--black)',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Background glow */}
      <div style={{
        position: 'absolute',
        width: '500px',
        height: '500px',
        borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(201,168,76,0.06) 0%, transparent 70%)',
        pointerEvents: 'none',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
      }} />

      {/* Ink drop */}
      <div style={{
        width: '36px',
        height: '36px',
        borderRadius: '50% 50% 50% 0',
        background: 'var(--gold)',
        transform: 'rotate(-45deg)',
        marginBottom: '24px',
        flexShrink: 0,
      }} />

      {/* Brand name */}
      <h1 style={{
        fontFamily: 'var(--font-display)',
        fontSize: 'clamp(44px, 9vw, 72px)',
        fontWeight: 300,
        letterSpacing: '0.04em',
        textAlign: 'center',
        lineHeight: 1.1,
        marginBottom: '8px',
      }}>
        Inkbook
      </h1>

      <p style={{
        color: 'var(--gold)',
        fontSize: '11px',
        letterSpacing: '0.22em',
        textTransform: 'uppercase',
        marginBottom: '44px',
      }}>
        Booking with Miguel · Austin, TX
      </p>

      {/* Hero */}
      <div style={{ textAlign: 'center', maxWidth: '320px', marginBottom: '36px' }}>
        <h2 style={{
          fontSize: 'clamp(20px, 5vw, 26px)',
          fontWeight: 300,
          lineHeight: 1.4,
          marginBottom: '14px',
        }}>
          Booking with Miguel<br />just got easy.
        </h2>
        <p style={{
          color: 'var(--text-muted)',
          fontSize: '14px',
          fontWeight: 300,
          lineHeight: 1.8,
        }}>
          No DMs. No waiting on an estimate.<br />No guessing on open dates.
        </p>
      </div>

      {/* How it works */}
      <div style={{
        width: '100%',
        maxWidth: '360px',
        border: '1px solid var(--border)',
        position: 'relative',
        marginBottom: '36px',
      }}>
        <div style={{ position: 'absolute', top: 0, left: 0, width: '20px', height: '20px', borderTop: '1px solid var(--gold)', borderLeft: '1px solid var(--gold)' }} />
        <div style={{ position: 'absolute', bottom: 0, right: 0, width: '20px', height: '20px', borderBottom: '1px solid var(--gold)', borderRight: '1px solid var(--gold)' }} />

        {[
          { step: '01', title: 'Describe your idea', sub: 'Answer 6 quick questions — takes about 2 minutes' },
          { step: '02', title: 'Get an instant estimate', sub: 'Real price range and deposit amount — no waiting' },
          { step: '03', title: 'Pick a real open date', sub: "Pulled from Miguel's live calendar — no back and forth" },
        ].map((item, i) => (
          <div key={i} style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: '16px',
            padding: '18px 22px',
            borderBottom: i < 2 ? '1px solid var(--border)' : 'none',
          }}>
            <span style={{
              fontFamily: 'var(--font-display)',
              fontSize: '10px',
              color: 'var(--gold)',
              letterSpacing: '0.1em',
              opacity: 0.6,
              marginTop: '3px',
              flexShrink: 0,
              width: '18px',
            }}>
              {item.step}
            </span>
            <div>
              <p style={{ fontSize: '13px', fontWeight: 500, marginBottom: '3px' }}>{item.title}</p>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 300, lineHeight: 1.5 }}>{item.sub}</p>
            </div>
          </div>
        ))}
      </div>

      {/* CTA button */}
      <button
        onClick={onStart}
        style={{
          width: '100%',
          maxWidth: '360px',
          padding: '16px',
          background: 'var(--gold)',
          color: 'var(--black)',
          fontSize: '12px',
          letterSpacing: '0.15em',
          textTransform: 'uppercase',
          fontWeight: 700,
          border: 'none',
          borderRadius: '2px',
          cursor: 'pointer',
          marginBottom: '20px',
          transition: 'opacity 0.15s ease',
        }}
        onMouseEnter={e => (e.currentTarget.style.opacity = '0.88')}
        onMouseLeave={e => (e.currentTarget.style.opacity = '1')}
      >
        Get My Estimate →
      </button>

      {/* Instagram */}
      <a
        href="https://www.instagram.com/miguel_tattoos"
        target="_blank"
        rel="noopener noreferrer"
        style={{
          color: 'var(--text-muted)',
          fontSize: '12px',
          letterSpacing: '0.06em',
          textDecoration: 'none',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          transition: 'color 0.15s ease',
        }}
        onMouseEnter={e => (e.currentTarget.style.color = 'var(--gold)')}
        onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <rect x="2" y="2" width="20" height="20" rx="5" ry="5"/>
          <circle cx="12" cy="12" r="4"/>
          <circle cx="17.5" cy="6.5" r="0.5" fill="currentColor"/>
        </svg>
        @miguel_tattoos
      </a>

      <p style={{
        color: 'var(--text-muted)',
        fontSize: '10px',
        letterSpacing: '0.1em',
        textTransform: 'uppercase',
        opacity: 0.35,
        marginTop: '40px',
      }}>
        Powered by Inkbook
      </p>
    </div>
  )
}