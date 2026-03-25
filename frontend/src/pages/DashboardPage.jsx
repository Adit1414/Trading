import {
  Bot, Activity, TrendingUp, DollarSign,
  Plus, Sparkles, ArrowUpRight, ArrowDownRight,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import MetricCard from '../components/MetricCard'
import PortfolioPerformanceCard from '../components/PortfolioPerformanceCard'

const RECENT_TRADES = [
  { id: 1, pair: 'BTC/USDT', side: 'BUY',  time: '2 mins ago',   profit: '+$145.20', isWin: true  },
  { id: 2, pair: 'ETH/USDT', side: 'SELL', time: '15 mins ago',  profit: '-$32.50',  isWin: false },
  { id: 3, pair: 'SOL/USDT', side: 'BUY',  time: '1 hour ago',   profit: '+$89.00',  isWin: true  },
  { id: 4, pair: 'AVAX/USDT',side: 'SELL', time: '3 hours ago',  profit: '+$12.40',  isWin: true  },
]

const MARKET_TICKERS = [
  { symbol: 'BTC', price: '$64,230', change: '+2.4%', isUp: true  },
  { symbol: 'ETH', price: '$3,450',  change: '-1.2%', isUp: false },
  { symbol: 'SOL', price: '$145.20', change: '+5.7%', isUp: true  },
  { symbol: 'BNB', price: '$590.00', change: '+0.8%', isUp: true  },
]

export default function DashboardPage() {
  const navigate = useNavigate()

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '32px 28px' }}>

      {/* ── Page Header ── */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '32px', gap: '16px', flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ fontSize: '26px', fontWeight: 700, color: 'white', letterSpacing: '-0.02em', lineHeight: 1 }}>
            Dashboard
          </h1>
          <p style={{ fontSize: '13px', color: '#64748b', marginTop: '6px' }}>
            Welcome back. Here is your real-time portfolio overview.
          </p>
        </div>

        {/* Action buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexShrink: 0 }}>
          <button
            onClick={() => navigate('/backtests')}
            style={{
              display: 'flex', alignItems: 'center', gap: '7px',
              padding: '9px 16px', borderRadius: '12px',
              background: 'rgba(129,140,248,0.1)',
              border: '1px solid rgba(129,140,248,0.2)',
              color: '#a5b4fc', fontSize: '13px', fontWeight: 600,
              cursor: 'pointer', transition: 'all 0.2s', whiteSpace: 'nowrap',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(129,140,248,0.18)'; e.currentTarget.style.borderColor = 'rgba(129,140,248,0.35)' }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(129,140,248,0.1)'; e.currentTarget.style.borderColor = 'rgba(129,140,248,0.2)' }}
          >
            <Sparkles size={15} strokeWidth={2} />
            New Backtest
          </button>
          <button
            onClick={() => navigate('/bots')}
            style={{
              display: 'flex', alignItems: 'center', gap: '7px',
              padding: '9px 18px', borderRadius: '12px',
              background: 'linear-gradient(135deg, #818cf8 0%, #6366f1 100%)',
              border: 'none',
              color: 'white', fontSize: '13px', fontWeight: 600,
              cursor: 'pointer', transition: 'all 0.2s', whiteSpace: 'nowrap',
              boxShadow: '0 4px 18px rgba(99,102,241,0.4)',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.opacity = '0.88' }}
            onMouseLeave={(e) => { e.currentTarget.style.opacity = '1' }}
          >
            <Plus size={15} strokeWidth={2.5} />
            Create Bot
          </button>
        </div>
      </div>

      {/* ── KPI Cards ── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '20px',
          marginBottom: '28px',
        }}
      >
        <MetricCard title="Active Bots"   value="7"      icon={Bot}       trend="+1"    />
        <MetricCard title="Total Trades"  value="342"    icon={Activity}  trend="+12"   />
        <MetricCard title="Win Rate"      value="73.4%"  icon={TrendingUp} trend="+2.1%" />
        <MetricCard title="Avg Return"    value="2.8%"   icon={DollarSign} trend="-0.4%" />
      </div>

      {/* ── Portfolio Chart ── */}
      <PortfolioPerformanceCard />

      {/* ── Bottom Section ── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(0,2fr) minmax(0,1fr)',
          gap: '20px',
        }}
        className="dashboard-bottom-grid"
      >
        {/* Recent Executions */}
        <div
          style={{
            background: 'linear-gradient(145deg, #131b2f 0%, #0f1729 100%)',
            border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: '20px',
            padding: '24px 28px',
            boxShadow: '0 4px 24px rgba(0,0,0,0.25)',
          }}
        >
          <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'white', marginBottom: '20px' }}>
            Recent Executions
          </h3>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  {['Pair', 'Side', 'Time', 'Profit / Loss'].map((h, i) => (
                    <th
                      key={h}
                      style={{
                        paddingBottom: '12px',
                        fontSize: '10px', fontWeight: 700,
                        color: '#334155', letterSpacing: '0.1em', textTransform: 'uppercase',
                        textAlign: i === 3 ? 'right' : 'left',
                      }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {RECENT_TRADES.map((trade, idx) => (
                  <tr
                    key={trade.id}
                    style={{
                      borderBottom: idx < RECENT_TRADES.length - 1 ? '1px solid rgba(255,255,255,0.04)' : 'none',
                      transition: 'background 0.15s',
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.02)' }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent' }}
                  >
                    <td style={{ padding: '14px 0', fontSize: '14px', fontWeight: 600, color: 'white' }}>
                      {trade.pair}
                    </td>
                    <td style={{ padding: '14px 0' }}>
                      <span style={{
                        padding: '3px 10px', borderRadius: '6px',
                        fontSize: '11px', fontWeight: 700, letterSpacing: '0.05em',
                        background: trade.side === 'BUY' ? 'rgba(16,185,129,0.1)' : 'rgba(244,63,94,0.1)',
                        color: trade.side === 'BUY' ? '#10b981' : '#f43f5e',
                        border: `1px solid ${trade.side === 'BUY' ? 'rgba(16,185,129,0.2)' : 'rgba(244,63,94,0.2)'}`,
                      }}>
                        {trade.side}
                      </span>
                    </td>
                    <td style={{ padding: '14px 0', fontSize: '13px', color: '#475569' }}>
                      {trade.time}
                    </td>
                    <td style={{
                      padding: '14px 0', textAlign: 'right',
                      fontSize: '14px', fontWeight: 700,
                      color: trade.isWin ? '#10b981' : '#f43f5e',
                    }}>
                      {trade.profit}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Market Overview */}
        <div
          style={{
            background: 'linear-gradient(145deg, #131b2f 0%, #0f1729 100%)',
            border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: '20px',
            padding: '24px',
            boxShadow: '0 4px 24px rgba(0,0,0,0.25)',
          }}
        >
          <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'white', marginBottom: '16px' }}>
            Market Overview
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            {MARKET_TICKERS.map((ticker) => (
              <div
                key={ticker.symbol}
                style={{
                  padding: '14px',
                  borderRadius: '14px',
                  border: '1px solid rgba(255,255,255,0.05)',
                  background: ticker.isUp ? 'rgba(16,185,129,0.03)' : 'rgba(244,63,94,0.03)',
                  transition: 'all 0.2s',
                  cursor: 'default',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = ticker.isUp ? 'rgba(16,185,129,0.15)' : 'rgba(244,63,94,0.15)'
                  e.currentTarget.style.background = ticker.isUp ? 'rgba(16,185,129,0.07)' : 'rgba(244,63,94,0.06)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'rgba(255,255,255,0.05)'
                  e.currentTarget.style.background = ticker.isUp ? 'rgba(16,185,129,0.03)' : 'rgba(244,63,94,0.03)'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <span style={{ fontSize: '11px', fontWeight: 700, color: '#64748b' }}>{ticker.symbol}</span>
                  {ticker.isUp
                    ? <ArrowUpRight size={14} style={{ color: '#10b981' }} />
                    : <ArrowDownRight size={14} style={{ color: '#f43f5e' }} />
                  }
                </div>
                <p style={{ fontSize: '15px', fontWeight: 700, color: 'white', lineHeight: 1, marginBottom: '4px' }}>
                  {ticker.price}
                </p>
                <p style={{ fontSize: '11px', fontWeight: 700, color: ticker.isUp ? '#10b981' : '#f43f5e' }}>
                  {ticker.change}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Responsive bottom grid fix */}
      <style>{`
        @media (max-width: 900px) {
          .dashboard-bottom-grid {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </div>
  )
}