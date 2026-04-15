import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from 'recharts'
import { MoreHorizontal, ChevronDown, TrendingUp, Activity } from 'lucide-react'


const CustomAnnotationDot = (props) => {
  const { cx, cy, payload } = props
  if (!payload.action) return null
  const isBuy  = payload.action === 'BUY'
  const color  = isBuy ? '#10b981' : '#f43f5e'
  const bgOpacity = isBuy ? 0.18 : 0.18
  return (
    <g transform={`translate(${cx},${cy})`}>
      <circle r={5} fill={color} stroke="#131b2f" strokeWidth={2.5} />
      <rect x={-22} y={-34} width={44} height={19} rx={9.5}
        fill={`rgba(${isBuy ? '16,185,129' : '244,63,94'},${bgOpacity})`}
        stroke={color} strokeWidth={1}
      />
      <text x={0} y={-20} textAnchor="middle" fill={color}
        fontSize={10} fontWeight="700" fontFamily="Inter, sans-serif">
        {payload.action}
      </text>
    </g>
  )
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: '#1a233a',
      border: '1px solid rgba(255,255,255,0.1)',
      borderRadius: '14px',
      padding: '12px 16px',
      boxShadow: '0 12px 32px rgba(0,0,0,0.5)',
    }}>
      <p style={{ fontSize: '11px', color: '#64748b', marginBottom: '4px', fontWeight: 500 }}>{label}</p>
      <p style={{ fontSize: '11px', color: '#64748b', marginBottom: '4px', fontWeight: 500 }}>{label}</p>
      <p style={{ fontSize: '16px', fontWeight: 700, color: 'white' }}>
        ${payload[0].value?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
      </p>
    </div>
  )
}

export default function PortfolioPerformanceCard({
  data = [],
  title = "Portfolio Performance",
  currentBalance = 0,
  pnlPercent = "0.00",
  rawPnl = 0,
  activeTimeframe = '1D',
  setActiveTimeframe,
  isError = false,
  errorMessage = "Live API Error or No Keys",
  mode = undefined, // "PAPER" or "LIVE" or undefined
  onModeChange = undefined, // Function to switch mode
  compact = false // If true, shrink paddings
}) {
  const pnlPrefix = rawPnl >= 0 ? '+' : '';
  const pnlColor = rawPnl >= 0 ? '#10b981' : '#f43f5e';
  const pnlBg = rawPnl >= 0 ? 'rgba(16,185,129,0.1)' : 'rgba(244,63,94,0.1)';
  const pnlBorder = rawPnl >= 0 ? 'rgba(16,185,129,0.25)' : 'rgba(244,63,94,0.25)';
  return (
    <div
      style={{
        background: 'linear-gradient(145deg, #131b2f 0%, #0f1729 100%)',
        border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: compact ? '16px' : '20px',
        padding: compact ? '24px' : '28px',
        marginBottom: compact ? '0px' : '28px',
        boxShadow: '0 4px 24px rgba(0,0,0,0.25)',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px', gap: '16px', flexWrap: 'wrap' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '6px' }}>
            <p style={{ fontSize: '12px', color: '#64748b', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase' }}>
              {title}
            </p>
            {onModeChange && (
              <div style={{ display: 'flex', background: 'rgba(0,0,0,0.2)', borderRadius: '6px', padding: '2px' }}>
                <button
                  onClick={() => onModeChange('PAPER')}
                  style={{
                    padding: '4px 8px', fontSize: '10px', fontWeight: 700, borderRadius: '4px', border: 'none', cursor: 'pointer', transition: 'all 0.2s',
                    background: mode === 'PAPER' ? '#3b82f6' : 'transparent', color: mode === 'PAPER' ? 'white' : '#64748b'
                  }}
                >
                  PAPER
                </button>
                <button
                  onClick={() => onModeChange('LIVE')}
                  style={{
                     padding: '4px 8px', fontSize: '10px', fontWeight: 700, borderRadius: '4px', border: 'none', cursor: 'pointer', transition: 'all 0.2s',
                    background: mode === 'LIVE' ? '#3b82f6' : 'transparent', color: mode === 'LIVE' ? 'white' : '#64748b'
                  }}
                >
                  LIVE
                </button>
              </div>
            )}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <h2 style={{ fontSize: compact ? '28px' : '34px', fontWeight: 700, color: 'white', letterSpacing: '-0.04em', lineHeight: 1 }}>
              ${currentBalance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </h2>
            <span style={{
              display: 'flex', alignItems: 'center', gap: '4px',
              padding: '4px 10px', borderRadius: '8px',
              fontSize: '12px', fontWeight: 700,
              background: pnlBg,
              border: `1px solid ${pnlBorder}`,
              color: pnlColor,
            }}>
              <TrendingUp size={12} strokeWidth={2.5} />
              {pnlPrefix}{pnlPercent}%
            </span>
          </div>
          {/* Sub stats */}
          <div style={{ display: 'flex', gap: '20px', marginTop: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <Activity size={12} style={{ color: isError ? '#f43f5e' : '#475569' }} />
              <span style={{ fontSize: '12px', color: isError ? '#f43f5e' : '#64748b' }}>
                {isError ? errorMessage : (mode === 'PAPER' ? "Synced via Testnet" : "Synced Live")}
              </span>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'rgba(0,0,0,0.2)', padding: '4px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.05)' }}>
          {['1H', '4H', '1D', '1W'].map((tf) => (
            <button
              key={tf}
              onClick={() => setActiveTimeframe && setActiveTimeframe(tf)}
              style={{
                padding: '6px 12px', borderRadius: '8px',
                background: activeTimeframe === tf ? '#3b82f6' : 'transparent',
                border: 'none',
                color: activeTimeframe === tf ? 'white' : '#94a3b8', 
                fontSize: '12px', fontWeight: 700,
                cursor: 'pointer', transition: 'all 0.2s',
              }}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      {/* Chart */}
      <div style={{ height: '300px', width: '100%' }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 38, right: 16, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="portfolioGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%"   stopColor="#818cf8" stopOpacity={0.45} />
                <stop offset="100%" stopColor="#818cf8" stopOpacity={0} />
              </linearGradient>
            </defs>

            <CartesianGrid
              strokeDasharray="3 3"
              vertical={false}
              stroke="rgba(255,255,255,0.04)"
            />

            <XAxis
              dataKey="name"
              axisLine={false}
              tickLine={false}
              tick={{ fill: '#475569', fontSize: 11, fontFamily: 'Inter, sans-serif' }}
              dy={10}
            />

            <YAxis
              axisLine={false}
              tickLine={false}
              tick={{ fill: '#475569', fontSize: 11, fontFamily: 'Inter, sans-serif' }}
              tickFormatter={(v) => `$${(v / 1000).toFixed(1)}k`}
              domain={['dataMin', 'dataMax']}
              width={60}
            />

            <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.08)', strokeWidth: 1, strokeDasharray: '4 4' }} />

            <Area
              type="monotone"
              dataKey="equity"
              stroke="#818cf8"
              strokeWidth={2.5}
              fillOpacity={1}
              fill="url(#portfolioGrad)"
              activeDot={{ r: 6, fill: '#818cf8', stroke: '#0f1729', strokeWidth: 3 }}
              dot={<CustomAnnotationDot />}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}