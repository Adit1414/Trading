import { TrendingUp, TrendingDown } from 'lucide-react'

export default function MetricCard({ title, value, icon: Icon, trend }) {
  const isPositive = trend?.startsWith('+')

  return (
    <div
      className="relative overflow-hidden group"
      style={{
        background: 'linear-gradient(145deg, #131b2f 0%, #0f1729 100%)',
        border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: '20px',
        padding: '24px',
        minHeight: '160px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        transition: 'border-color 0.25s, box-shadow 0.25s',
        boxShadow: '0 4px 24px rgba(0,0,0,0.25)',
        cursor: 'default',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = 'rgba(129,140,248,0.2)'
        e.currentTarget.style.boxShadow = '0 8px 32px rgba(0,0,0,0.35), 0 0 0 1px rgba(129,140,248,0.08)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)'
        e.currentTarget.style.boxShadow = '0 4px 24px rgba(0,0,0,0.25)'
      }}
    >
      {/* Subtle background glow */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: 'radial-gradient(ellipse at top left, rgba(129,140,248,0.04) 0%, transparent 60%)',
          borderRadius: '20px',
          pointerEvents: 'none',
        }}
      />

      {/* Top row: icon + trend badge */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', position: 'relative' }}>
        {/* Icon container */}
        <div
          style={{
            width: '44px',
            height: '44px',
            borderRadius: '12px',
            background: 'rgba(129,140,248,0.12)',
            border: '1px solid rgba(129,140,248,0.2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          <Icon size={20} strokeWidth={2} style={{ color: '#818cf8' }} />
        </div>

        {/* Trend badge */}
        {trend && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: '4px 10px',
              borderRadius: '8px',
              fontSize: '11px',
              fontWeight: 700,
              border: '1px solid',
              borderColor: isPositive ? 'rgba(16,185,129,0.25)' : 'rgba(244,63,94,0.25)',
              background: isPositive ? 'rgba(16,185,129,0.08)' : 'rgba(244,63,94,0.08)',
              color: isPositive ? '#10b981' : '#f43f5e',
            }}
          >
            {isPositive
              ? <TrendingUp size={11} strokeWidth={2.5} />
              : <TrendingDown size={11} strokeWidth={2.5} />
            }
            {trend}
          </div>
        )}
      </div>

      {/* Bottom: value + title */}
      <div style={{ position: 'relative' }}>
        <h3
          style={{
            fontSize: '30px',
            fontWeight: 700,
            color: 'white',
            letterSpacing: '-0.03em',
            lineHeight: 1,
            marginBottom: '8px',
          }}
        >
          {value}
        </h3>
        <p
          style={{
            fontSize: '11px',
            fontWeight: 600,
            color: '#475569',
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
          }}
        >
          {title}
        </p>
      </div>

      {/* Bottom accent line */}
      <div
        style={{
          position: 'absolute',
          bottom: 0,
          left: '20%',
          right: '20%',
          height: '2px',
          borderRadius: '2px 2px 0 0',
          background: isPositive
            ? 'linear-gradient(90deg, transparent, rgba(16,185,129,0.5), transparent)'
            : 'linear-gradient(90deg, transparent, rgba(244,63,94,0.4), transparent)',
        }}
      />
    </div>
  )
}