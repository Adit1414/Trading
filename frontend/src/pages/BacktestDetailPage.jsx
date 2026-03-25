import { useParams, useNavigate } from 'react-router-dom'
import { useBacktestDetail } from '../api/backtests'
import { useState } from 'react'
import { ArrowLeft, Download, BarChart2, Settings2, Activity } from 'lucide-react'

export default function BacktestDetailPage() {
  const { id }       = useParams()
  const navigate     = useNavigate()
  const { data, isLoading, isError, error } = useBacktestDetail(id)
  const [activeTab, setActiveTab] = useState('Overview')

  if (isLoading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', flexDirection: 'column', gap: '12px' }}>
      <div style={{ width: '32px', height: '32px', border: '2px solid rgba(129,140,248,0.2)', borderTopColor: '#818cf8', borderRadius: '50%', animation: 'spin-cw 0.8s linear infinite' }} />
      <p style={{ fontSize: '13px', color: '#475569' }}>Loading backtest details…</p>
    </div>
  )

  if (isError) return (
    <div style={{ padding: '40px', textAlign: 'center', background: 'rgba(19,27,47,0.8)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '20px', maxWidth: '500px', margin: '40px auto' }}>
      <p style={{ color: '#f43f5e', fontWeight: 600, marginBottom: '8px' }}>Failed to load backtest.</p>
      <p style={{ fontSize: '12px', color: '#475569', marginBottom: '20px' }}>{error?.message}</p>
      <button
        onClick={() => navigate('/backtests')}
        style={{ padding: '9px 18px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '10px', color: 'white', fontSize: '13px', cursor: 'pointer' }}
      >
        ← Back to Backtests
      </button>
    </div>
  )

  if (!data) return null

  const metrics    = data.metrics    || {}
  const parameters = data.parameters || {}
  const status     = data.status     || 'COMPLETED'
  const isCompleted = status === 'COMPLETED'

  // Human-friendly title: prefer explicit name, else use date
  const runDate     = new Date(data.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  const displayName = data.name && !data.name.match(/^[0-9a-f-]{36}/i)
    ? data.name
    : `Backtest Run — ${runDate}`
  const shortId     = data.strategy_id?.slice(-8).toUpperCase()

  const handleExport = () => {
    const html = data.chart_html || metrics.chart_html
    if (!html) return
    const blob = new Blob([html], { type: 'text/html' })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href = url; a.download = `backtest_${data.symbol}_${runDate}.html`
    document.body.appendChild(a); a.click()
    document.body.removeChild(a); URL.revokeObjectURL(url)
  }

  const statusStyle = {
    COMPLETED: { bg: 'rgba(16,185,129,0.1)',  color: '#10b981', border: 'rgba(16,185,129,0.25)'  },
    RUNNING:   { bg: 'rgba(129,140,248,0.1)', color: '#818cf8', border: 'rgba(129,140,248,0.25)' },
    ERROR:     { bg: 'rgba(244,63,94,0.1)',   color: '#f43f5e', border: 'rgba(244,63,94,0.25)'   },
  }[status] || statusStyle?.COMPLETED

  const tabs = [
    { id: 'Overview',   icon: BarChart2  },
    { id: 'Parameters', icon: Settings2  },
    { id: 'Statistics', icon: Activity   },
  ]

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '32px 28px' }}>

      {/* ── Header ── */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '16px', marginBottom: '28px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '16px' }}>
          {/* Back button */}
          <button
            onClick={() => navigate('/backtests')}
            style={{
              width: '40px', height: '40px', borderRadius: '12px', flexShrink: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
              color: '#64748b', cursor: 'pointer', transition: 'all 0.2s', marginTop: '2px',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.color = 'white'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.15)' }}
            onMouseLeave={(e) => { e.currentTarget.style.color = '#64748b'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)' }}
          >
            <ArrowLeft size={18} strokeWidth={2} />
          </button>

          <div>
            {/* Name + status badge */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px', flexWrap: 'wrap' }}>
              <h1 style={{ fontSize: '22px', fontWeight: 700, color: 'white', letterSpacing: '-0.02em', lineHeight: 1 }}>
                {displayName}
              </h1>
              <span style={{
                padding: '3px 10px', borderRadius: '6px',
                fontSize: '10px', fontWeight: 800, letterSpacing: '0.1em', textTransform: 'uppercase',
                background: statusStyle?.bg, color: statusStyle?.color,
                border: `1px solid ${statusStyle?.border}`,
              }}>
                {status}
              </span>
            </div>

            {/* Sub-info row */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <span style={{
                padding: '3px 10px', borderRadius: '6px',
                fontSize: '11px', fontWeight: 600, color: '#94a3b8',
                background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)',
              }}>
                {data.strategy_id?.replace(/_/g, ' ')}
              </span>
              <span style={{ color: '#334155', fontSize: '12px' }}>•</span>
              <span style={{ fontSize: '13px', fontWeight: 600, color: 'white' }}>{data.symbol}</span>
              <span style={{ color: '#334155', fontSize: '12px' }}>•</span>
              <span style={{ fontSize: '11px', color: '#475569', fontFamily: 'monospace' }}>#{shortId}</span>
            </div>
          </div>
        </div>

        {/* Export button */}
        <button
          onClick={handleExport}
          disabled={!data.chart_html && !metrics.chart_html}
          style={{
            display: 'flex', alignItems: 'center', gap: '7px',
            padding: '9px 16px', borderRadius: '12px',
            background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
            color: '#94a3b8', fontSize: '13px', fontWeight: 500, cursor: 'pointer',
            transition: 'all 0.2s', whiteSpace: 'nowrap',
            opacity: (!data.chart_html && !metrics.chart_html) ? 0.4 : 1,
          }}
          onMouseEnter={(e) => { if (data.chart_html || metrics.chart_html) { e.currentTarget.style.color = 'white'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.15)' } }}
          onMouseLeave={(e) => { e.currentTarget.style.color = '#94a3b8'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)' }}
        >
          <Download size={15} strokeWidth={2} />
          Export Report
        </button>
      </div>

      {/* ── Tabs ── */}
      <div style={{ display: 'flex', gap: '4px', marginBottom: '24px', padding: '4px', background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '14px', width: 'fit-content' }}>
        {tabs.map(({ id: tabId, icon: TabIcon }) => {
          const active = activeTab === tabId
          return (
            <button
              key={tabId}
              onClick={() => setActiveTab(tabId)}
              style={{
                display: 'flex', alignItems: 'center', gap: '7px',
                padding: '8px 16px', borderRadius: '10px',
                fontSize: '13px', fontWeight: active ? 600 : 500,
                border: active ? '1px solid rgba(129,140,248,0.2)' : '1px solid transparent',
                background: active ? 'rgba(129,140,248,0.1)' : 'transparent',
                color: active ? 'white' : '#64748b',
                cursor: 'pointer', transition: 'all 0.18s', whiteSpace: 'nowrap',
              }}
              onMouseEnter={(e) => { if (!active) e.currentTarget.style.color = '#94a3b8' }}
              onMouseLeave={(e) => { if (!active) e.currentTarget.style.color = '#64748b' }}
            >
              <TabIcon size={14} strokeWidth={2} />
              {tabId}
            </button>
          )
        })}
      </div>

      {/* ── Tab Content ── */}
      {activeTab === 'Overview' && (
        <div>
          {(data.chart_html || metrics.chart_html) ? (
            <div style={{ background: 'linear-gradient(145deg,#131b2f,#0f1729)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '20px', overflow: 'hidden', boxShadow: '0 4px 24px rgba(0,0,0,0.3)' }}>
              <div style={{ padding: '22px 24px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'white' }}>Portfolio Performance</h3>
                <p style={{ fontSize: '12px', color: '#475569', marginTop: '3px' }}>Interactive simulation equity curve</p>
              </div>
              <div style={{ padding: '8px' }}>
                <iframe
                  srcDoc={data.chart_html || metrics.chart_html}
                  sandbox="allow-scripts allow-popups"
                  style={{ width: '100%', height: '600px', borderRadius: '14px', border: 'none', display: 'block' }}
                  title="Backtest Chart"
                />
              </div>
            </div>
          ) : (
            <div style={{ background: 'linear-gradient(145deg,#131b2f,#0f1729)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '20px', padding: '80px', textAlign: 'center' }}>
              <p style={{ color: '#475569' }}>No chart data available for this run.</p>
            </div>
          )}
        </div>
      )}

      {activeTab === 'Parameters' && (
        <div style={{ background: 'linear-gradient(145deg,#131b2f,#0f1729)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '20px', overflow: 'hidden', boxShadow: '0 4px 24px rgba(0,0,0,0.25)' }}>
          <div style={{ padding: '22px 24px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'white' }}>Simulation Parameters</h3>
          </div>
          <div style={{ padding: '20px', display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '12px' }}>
            {Object.keys(parameters).length > 0 ? (
              Object.entries(parameters).map(([key, val]) => (
                <div key={key} style={{ background: 'rgba(0,0,0,0.2)', padding: '14px 16px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
                  <p style={{ fontSize: '10px', color: '#334155', letterSpacing: '0.1em', textTransform: 'uppercase', fontWeight: 700, marginBottom: '6px' }}>
                    {key.replace(/_/g, ' ')}
                  </p>
                  <p style={{ fontSize: '13px', fontWeight: 600, color: 'white' }}>
                    {typeof val === 'object' ? JSON.stringify(val) : String(val ?? '—')}
                  </p>
                </div>
              ))
            ) : (
              <p style={{ fontSize: '13px', color: '#475569', gridColumn: '1 / -1' }}>No parameters recorded.</p>
            )}
          </div>
        </div>
      )}

      {activeTab === 'Statistics' && (
        <div style={{ background: 'linear-gradient(145deg,#131b2f,#0f1729)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '20px', overflow: 'hidden', boxShadow: '0 4px 24px rgba(0,0,0,0.25)' }}>
          <div style={{ padding: '22px 24px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'white' }}>Performance Statistics</h3>
          </div>
          <div style={{ padding: '20px', display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '12px' }}>
            {Object.keys(metrics).length > 0 ? (
              Object.entries(metrics).map(([key, val]) => {
                const isGood = (key.includes('return_pct') || key.includes('win_rate') || key.includes('profit_factor')) && val > 0
                const isBad  = (key.includes('return_pct') || key.includes('win_rate') || key.includes('profit_factor')) && val < 0
                return (
                  <div key={key} style={{ background: 'rgba(0,0,0,0.2)', padding: '14px 16px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
                    <p style={{ fontSize: '10px', color: '#334155', letterSpacing: '0.1em', textTransform: 'uppercase', fontWeight: 700, marginBottom: '6px' }}>
                      {key.replace(/_/g, ' ')}
                    </p>
                    <p style={{ fontSize: '14px', fontWeight: 700, color: isGood ? '#10b981' : isBad ? '#f43f5e' : 'white' }}>
                      {val !== null && val !== undefined ? String(val) : '—'}
                    </p>
                  </div>
                )
              })
            ) : (
              <p style={{ fontSize: '13px', color: '#475569', gridColumn: '1 / -1' }}>No statistics recorded.</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}