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
        padding: '40px 24px',
        background: 'var(--black)',
        position: 'relative',
        overflow: 'hidden',
      }}>
        {/* Subtle gold glow behind center */}
        <div style={{
          position: 'absolute',
          width: '400px',
          height: '400px',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(201,168,76,0.07) 0%, transparent 70%)',
          pointerEvents: 'none',
        }} />
  
        {/* Ink drop mark */}
        <div style={{
          width: '48px',
          height: '48px',
          borderRadius: '50% 50% 50% 0',
          background: 'var(--gold)',
          transform: 'rotate(-45deg)',
          marginBottom: '32px',
          opacity: 0.9,
        }} />
  
        <h1 style={{
          fontFamily: 'var(--font-display)',
          fontSize: 'clamp(42px, 8vw, 72px)',
          fontWeight: 300,
          letterSpacing: '0.04em',
          textAlign: 'center',
          lineHeight: 1.1,
          marginBottom: '16px',
        }}>
          Inkbook
        </h1>
  
        <p style={{
          color: 'var(--gold)',
          fontFamily: 'var(--font-body)',
          fontSize: '13px',
          fontWeight: 400,
          letterSpacing: '0.2em',
          textTransform: 'uppercase',
          marginBottom: '12px',
        }}>
          Tattoo Booking
        </p>
  
        <p style={{
          color: 'var(--text-muted)',
          fontSize: '15px',
          fontWeight: 300,
          textAlign: 'center',
          maxWidth: '300px',
          lineHeight: 1.7,
          marginBottom: '48px',
        }}>
          Describe your vision. Get an instant price estimate and available date.
        </p>
  
        <button
          onClick={onStart}
          style={{
            padding: '16px 40px',
            border: '1px solid var(--gold)',
            background: 'transparent',
            color: 'var(--gold)',
            fontSize: '13px',
            letterSpacing: '0.15em',
            textTransform: 'uppercase',
            fontWeight: 500,
            transition: 'all 0.2s ease',
          }}
          onMouseEnter={e => {
            (e.target as HTMLButtonElement).style.background = 'var(--gold)'
            ;(e.target as HTMLButtonElement).style.color = 'var(--black)'
          }}
          onMouseLeave={e => {
            (e.target as HTMLButtonElement).style.background = 'transparent'
            ;(e.target as HTMLButtonElement).style.color = 'var(--gold)'
          }}
        >
          Start Your Booking
        </button>
  
        <p style={{
          position: 'absolute',
          bottom: '24px',
          color: 'var(--text-muted)',
          fontSize: '11px',
          letterSpacing: '0.1em',
        }}>
          BY MIGUEL · EST. 2024
        </p>
      </div>
    )
  }