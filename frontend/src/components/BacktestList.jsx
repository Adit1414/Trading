import { useNavigate } from 'react-router-dom'
import { useBacktests } from '../api/backtests'
import { useState } from 'react'
import { CheckCircle2, Clock, AlertTriangle, Eye, Trash2, Activity, TrendingUp, TrendingDown } from 'lucide-react'

function timeAgo(dateString) {
  const diff = Math.floor((Date.now() - new Date(dateString)) / 1000)
  if (diff < 60)    return 'Just now'
  if (diff < 3600)  return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  if (diff < 172800) return 'Yesterday'
  return `${Math.floor(diff / 86400)}d ago`
}

function ReturnBar({ pct }) {
  if (pct === null || pct === undefined) return null
  const clamped = Math.min(Math.abs(pct), 100)
  const isPos   = pct >= 0
  return (
    <div style={{ marginTop: '8px', height: '3px', background: 'rgba(255,255,255,0.06)', borderRadius: '2px', overflow: 'hidden' }}>
      <div style={{
        height: '100%',
        width: `${clamped}%`,
        borderRadius: '2px',
        background: isPos
          ? 'linear-gradient(90deg, rgba(16,185,129,0.4), #10b981)'
          : 'linear-gradient(90deg, rgba(244,63,94,0.4), #f43f5e)',
        transition: 'width 0.6s ease',
      }} />
    </div>
  )
}

export default function BacktestList({ searchQuery }) {
  const navigate = useNavigate()
  const [page, setPage]  = useState(0)
  const limit  = 20
  const offset = page * limit

  const { data: backtests, isLoading, isError, error } = useBacktests(limit, offset)

  if (isLoading) return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '64px 0', gap: '12px', background: 'linear-gradient(145deg,#131b2f,#0f1729)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '20px' }}>
      <div style={{ width: '28px', height: '28px', border: '2px solid rgba(129,140,248,0.2)', borderTopColor: '#818cf8', borderRadius: '50%', animation: 'spin-cw 0.8s linear infinite' }} />
      <p style={{ fontSize: '13px', color: '#475569' }}>Loading simulations…</p>
    </div>
  )

  if (isError) return (
    <div style={{ textAlign: 'center', padding: '64px 0', background: 'linear-gradient(145deg,#131b2f,#0f1729)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '20px' }}>
      <p style={{ color: '#f43f5e', fontSize: '14px', fontWeight: 600 }}>Failed to load backtests.</p>
      <p style={{ fontSize: '12px', color: '#475569', marginTop: '4px' }}>{error?.message}</p>
    </div>
  )

  if (!backtests || backtests.length === 0) return (
    <div style={{ textAlign: 'center', padding: '64px 0', background: 'linear-gradient(145deg,#131b2f,#0f1729)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '20px' }}>
      <Activity size={32} style={{ color: '#334155', margin: '0 auto 12px' }} />
      <p style={{ color: '#64748b', fontSize: '14px', fontWeight: 500 }}>No simulations yet.</p>
      <p style={{ fontSize: '12px', color: '#334155', marginTop: '4px' }}>Run your first simulation to see results here.</p>
    </div>
  )

  const filtered = backtests.filter(bt => {
    if (!searchQuery) return true
    const q = searchQuery.toLowerCase()
    const name = (bt.name || `${bt.strategy_id} Run`).toLowerCase()
    return (bt.symbol?.toLowerCase().includes(q)) ||
           (bt.strategy_id?.toLowerCase().includes(q)) ||
           name.includes(q)
  })

  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '18px' }}>
        {filtered.map((bt) => {
          const returnPct = bt.total_return_pct
          const isPos     = returnPct !== null && returnPct > 0
          const isNeg     = returnPct !== null && returnPct < 0
          const status    = bt.status || 'COMPLETED'

          const statusMap = {
            COMPLETED: { icon: CheckCircle2, color: '#10b981', bg: 'rgba(16,185,129,0.1)',  border: 'rgba(16,185,129,0.2)'  },
            RUNNING:   { icon: Clock,        color: '#818cf8', bg: 'rgba(129,140,248,0.1)', border: 'rgba(129,140,248,0.2)' },
            ERROR:     { icon: AlertTriangle,color: '#f43f5e', bg: 'rgba(244,63,94,0.1)',   border: 'rgba(244,63,94,0.2)'   },
          }
          const s = statusMap[status] || statusMap.COMPLETED
          const StatusIcon = s.icon

          // Return size: visually scale large returns
          const returnFontSize = returnPct !== null
            ? (Math.abs(returnPct) >= 30 ? '30px' : Math.abs(returnPct) >= 10 ? '26px' : '22px')
            : '22px'

          const displayName = bt.name || `Run — ${new Date(bt.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`
          const stratLabel  = bt.strategy_id?.replace(/_/g, ' ') || 'Unknown'

          return (
            <div
              key={bt.id}
              style={{
                background: 'linear-gradient(145deg, #131b2f 0%, #0f1729 100%)',
                border: '1px solid rgba(255,255,255,0.06)',
                borderRadius: '18px',
                padding: '22px',
                display: 'flex',
                flexDirection: 'column',
                gap: '16px',
                boxShadow: '0 4px 20px rgba(0,0,0,0.2)',
                transition: 'border-color 0.2s, box-shadow 0.2s',
                cursor: 'default',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'rgba(129,140,248,0.18)'
                e.currentTarget.style.boxShadow = '0 8px 32px rgba(0,0,0,0.3)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)'
                e.currentTarget.style.boxShadow = '0 4px 20px rgba(0,0,0,0.2)'
              }}
            >
              {/* Card top: icon + name + status */}
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px' }}>
                <div style={{
                  width: '42px', height: '42px', borderRadius: '12px', flexShrink: 0,
                  background: s.bg, border: `1px solid ${s.border}`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <StatusIcon size={20} strokeWidth={1.8} style={{ color: s.color }} />
                </div>

                <div style={{ flex: 1, minWidth: 0 }}>
                  <h3 style={{ fontSize: '14px', fontWeight: 700, color: 'white', lineHeight: 1.3, wordBreak: 'break-word' }}>
                    {displayName}
                  </h3>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '4px' }}>
                    <Clock size={11} style={{ color: '#475569', flexShrink: 0 }} />
                    <span style={{ fontSize: '11px', color: '#475569' }}>{timeAgo(bt.created_at)}</span>
                  </div>
                </div>

                <span style={{
                  padding: '3px 8px', borderRadius: '6px', flexShrink: 0,
                  fontSize: '9px', fontWeight: 800, letterSpacing: '0.1em', textTransform: 'uppercase',
                  background: s.bg, color: s.color, border: `1px solid ${s.border}`,
                }}>
                  {status}
                </span>
              </div>

              {/* Strategy + Market */}
              <div style={{
                display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px',
                padding: '14px', borderRadius: '12px',
                background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.04)',
              }}>
                <div>
                  <p style={{ fontSize: '10px', fontWeight: 700, color: '#334155', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '4px' }}>Strategy</p>
                  <p style={{ fontSize: '13px', fontWeight: 600, color: 'white', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={stratLabel}>
                    {stratLabel}
                  </p>
                </div>
                <div>
                  <p style={{ fontSize: '10px', fontWeight: 700, color: '#334155', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '4px' }}>Market</p>
                  <p style={{ fontSize: '13px', fontWeight: 600, color: 'white' }}>{bt.symbol}</p>
                </div>
              </div>

              {/* Return + actions */}
              <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', paddingTop: '4px', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                <div style={{ flex: 1 }}>
                  <p style={{ fontSize: '10px', fontWeight: 700, color: '#334155', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '6px' }}>
                    Total Return
                  </p>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    {returnPct !== null
                      ? (isPos ? <TrendingUp size={16} style={{ color: '#10b981' }} /> : <TrendingDown size={16} style={{ color: '#f43f5e' }} />)
                      : null
                    }
                    <p style={{
                      fontSize: returnFontSize,
                      fontWeight: 800,
                      letterSpacing: '-0.02em',
                      lineHeight: 1,
                      color: isPos ? '#10b981' : isNeg ? '#f43f5e' : '#94a3b8',
                    }}>
                      {returnPct !== null ? `${returnPct >= 0 ? '+' : ''}${returnPct.toFixed(2)}%` : '—'}
                    </p>
                  </div>
                  <ReturnBar pct={returnPct} />
                </div>

                <div style={{ display: 'flex', gap: '6px', marginLeft: '12px' }}>
                  <button
                    onClick={() => navigate(`/backtests/${bt.id}`)}
                    title="View details"
                    style={{
                      width: '34px', height: '34px', borderRadius: '10px',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      border: '1px solid rgba(255,255,255,0.07)',
                      background: 'rgba(255,255,255,0.03)', color: '#64748b',
                      cursor: 'pointer', transition: 'all 0.2s',
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.color = 'white'; e.currentTarget.style.background = 'rgba(255,255,255,0.08)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.14)' }}
                    onMouseLeave={(e) => { e.currentTarget.style.color = '#64748b'; e.currentTarget.style.background = 'rgba(255,255,255,0.03)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)' }}
                  >
                    <Eye size={15} strokeWidth={2} />
                  </button>
                  <button
                    title="Delete"
                    style={{
                      width: '34px', height: '34px', borderRadius: '10px',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      border: '1px solid rgba(255,255,255,0.07)',
                      background: 'rgba(255,255,255,0.03)', color: '#64748b',
                      cursor: 'pointer', transition: 'all 0.2s',
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.color = '#f43f5e'; e.currentTarget.style.background = 'rgba(244,63,94,0.08)'; e.currentTarget.style.borderColor = 'rgba(244,63,94,0.2)' }}
                    onMouseLeave={(e) => { e.currentTarget.style.color = '#64748b'; e.currentTarget.style.background = 'rgba(255,255,255,0.03)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)' }}
                  >
                    <Trash2 size={15} strokeWidth={2} />
                  </button>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Pagination */}
      {filtered.length > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '28px', paddingTop: '20px', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
          <p style={{ fontSize: '13px', color: '#475569', fontWeight: 500 }}>
            Showing {offset + 1}–{offset + filtered.length}
          </p>
          <div style={{ display: 'flex', gap: '8px' }}>
            {['Previous', 'Next'].map((label) => {
              const disabled = label === 'Previous' ? page === 0 : backtests?.length < limit
              return (
                <button
                  key={label}
                  onClick={() => setPage(label === 'Previous' ? Math.max(0, page - 1) : page + 1)}
                  disabled={disabled}
                  style={{
                    padding: '8px 18px', borderRadius: '10px',
                    fontSize: '13px', fontWeight: 600,
                    background: 'rgba(255,255,255,0.04)',
                    border: '1px solid rgba(255,255,255,0.08)',
                    color: disabled ? '#334155' : '#94a3b8',
                    cursor: disabled ? 'not-allowed' : 'pointer',
                    transition: 'all 0.2s', opacity: disabled ? 0.4 : 1,
                  }}
                  onMouseEnter={(e) => { if (!disabled) { e.currentTarget.style.color = 'white'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.14)' } }}
                  onMouseLeave={(e) => { e.currentTarget.style.color = disabled ? '#334155' : '#94a3b8'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)' }}
                >
                  {label}
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}