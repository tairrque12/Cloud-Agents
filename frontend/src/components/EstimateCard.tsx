import type { Estimate } from '../App'

interface Props {
  estimate: Estimate
  onReset: () => void
}

export default function EstimateCard({ estimate, onReset }: Props) {
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

      <p style={{ color: 'var(--text-muted)', fontSize: '12px', marginTop: '24px', textAlign: 'center', lineHeight: 1.6, maxWidth: '320px' }}>
        This is an AI-generated estimate. Miguel will confirm the final price and date after reviewing your request.
      </p>

      <button
        onClick={onReset}
        style={{
          marginTop: '32px',
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