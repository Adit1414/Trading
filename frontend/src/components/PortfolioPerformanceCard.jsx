import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from 'recharts'
import { MoreHorizontal, ChevronDown, TrendingUp, Activity } from 'lucide-react'

const data = [
  { time: '00:00', value: 124500 },
  { time: '02:00', value: 125500 },
  { time: '04:00', value: 127500, action: 'BUY' },
  { time: '06:00', value: 126000 },
  { time: '08:00', value: 124000 },
  { time: '10:00', value: 123500 },
  { time: '12:00', value: 125000 },
  { time: '14:00', value: 126500 },
  { time: '16:00', value: 129800, action: 'SELL' },
  { time: '18:00', value: 128000 },
  { time: '20:00', value: 128600 },
  { time: '22:00', value: 132100 },
]

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
      <p style={{ fontSize: '16px', fontWeight: 700, color: 'white' }}>
        ${payload[0].value.toLocaleString()}
      </p>
    </div>
  )
}

export default function PortfolioPerformanceCard() {
  return (
    <div
      style={{
        background: 'linear-gradient(145deg, #131b2f 0%, #0f1729 100%)',
        border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: '20px',
        padding: '28px',
        marginBottom: '28px',
        boxShadow: '0 4px 24px rgba(0,0,0,0.25)',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px', gap: '16px', flexWrap: 'wrap' }}>
        <div>
          <p style={{ fontSize: '12px', color: '#64748b', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: '6px' }}>
            Portfolio Performance
          </p>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <h2 style={{ fontSize: '34px', fontWeight: 700, color: 'white', letterSpacing: '-0.04em', lineHeight: 1 }}>
              $132,100.50
            </h2>
            <span style={{
              display: 'flex', alignItems: 'center', gap: '4px',
              padding: '4px 10px', borderRadius: '8px',
              fontSize: '12px', fontWeight: 700,
              background: 'rgba(16,185,129,0.1)',
              border: '1px solid rgba(16,185,129,0.25)',
              color: '#10b981',
            }}>
              <TrendingUp size={12} strokeWidth={2.5} />
              +8.4%
            </span>
          </div>
          {/* Sub stats */}
          <div style={{ display: 'flex', gap: '20px', marginTop: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <Activity size={12} style={{ color: '#475569' }} />
              <span style={{ fontSize: '12px', color: '#64748b' }}>24h change: </span>
              <span style={{ fontSize: '12px', color: '#10b981', fontWeight: 600 }}>+$10,442.50</span>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            style={{
              display: 'flex', alignItems: 'center', gap: '6px',
              padding: '7px 12px', borderRadius: '10px',
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.07)',
              color: '#94a3b8', fontSize: '12px', fontWeight: 500,
              cursor: 'pointer', transition: 'all 0.2s',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.07)'; e.currentTarget.style.color = 'white' }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; e.currentTarget.style.color = '#94a3b8' }}
          >
            Last 24 hours <ChevronDown size={13} />
          </button>
          <button
            style={{
              width: '34px', height: '34px', borderRadius: '10px',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              border: '1px solid transparent', color: '#64748b', cursor: 'pointer',
              transition: 'all 0.2s',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.05)'; e.currentTarget.style.color = 'white' }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#64748b' }}
          >
            <MoreHorizontal size={17} />
          </button>
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
              dataKey="time"
              axisLine={false}
              tickLine={false}
              tick={{ fill: '#475569', fontSize: 11, fontFamily: 'Inter, sans-serif' }}
              dy={10}
            />

            <YAxis
              axisLine={false}
              tickLine={false}
              tick={{ fill: '#475569', fontSize: 11, fontFamily: 'Inter, sans-serif' }}
              tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
              domain={['dataMin - 1200', 'dataMax + 1200']}
              width={52}
            />

            <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.08)', strokeWidth: 1, strokeDasharray: '4 4' }} />

            <Area
              type="monotone"
              dataKey="value"
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