import { Sparkles, TrendingUp, BarChart2, Activity, Zap, Shield, HelpCircle, Code } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

const DEFAULT_STRATEGIES = [
  {
    id: 'EMA_Crossover',
    name: 'EMA Crossover',
    description: 'A trend-following strategy that generates buy/sell signals on intersections of fast and slow EMAs.',
    tags: ['Trend', 'Medium Risk', 'Any Market'],
    icon: TrendingUp,
    color: '#818cf8',
    stats: { winRate: '64%', profitFactor: '1.4' }
  },
  {
    id: 'RSI_Divergence',
    name: 'RSI Divergence',
    description: 'Identifies potential market reversals by observing momentum decay against price action extremes.',
    tags: ['Reversal', 'High Reward', 'Ranging'],
    icon: Activity,
    color: '#f43f5e',
    stats: { winRate: '58%', profitFactor: '2.1' }
  },
  {
    id: 'Mean_Reversion',
    name: 'Bollinger Mean Reversion',
    description: 'Fades price extensions outside standard deviation bands expecting a return to the mean SMA.',
    tags: ['Counter-Trend', 'Low Risk', 'Ranging Market'],
    icon: BarChart2,
    color: '#10b981',
    stats: { winRate: '71%', profitFactor: '1.2' }
  },
  {
    id: 'Momentum_Breakout',
    name: 'Momentum Breakout',
    description: 'Capitalizes on extreme volume surges breaking out of defined consolidation ranges.',
    tags: ['Breakout', 'High Risk', 'Crypto'],
    icon: Zap,
    color: '#f59e0b',
    stats: { winRate: '45%', profitFactor: '3.5' }
  }
]

export default function StrategiesHubPage() {
  const navigate = useNavigate()

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '32px 28px' }}>
      {/* Page Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '32px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div
            style={{
              width: '48px', height: '48px', borderRadius: '14px',
              background: 'rgba(129,140,248,0.1)', border: '1px solid rgba(129,140,248,0.2)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#818cf8',
            }}
          >
            <Sparkles size={24} strokeWidth={2} />
          </div>
          <div>
            <h1 style={{ fontSize: '26px', fontWeight: 700, color: 'white', letterSpacing: '-0.02em', lineHeight: 1.2 }}>
              Strategies Central
            </h1>
            <p style={{ fontSize: '13px', color: '#94a3b8', marginTop: '4px' }}>
              Select a pre-built algorithmic edge or construct your own custom logic.
            </p>
          </div>
        </div>
        
        <button
          onClick={() => navigate('/code-editor')}
          style={{
            display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 20px', borderRadius: '12px',
            background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)',
            color: 'white', fontSize: '13px', fontWeight: 600, cursor: 'not-allowed', opacity: 0.6,
          }}
          title="Coming soon..."
        >
          <Code size={16} />
          Custom Script (Soon)
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '20px' }}>
        {DEFAULT_STRATEGIES.map((strategy) => (
          <div
            key={strategy.id}
            style={{
              background: 'linear-gradient(145deg, #131b2f 0%, #0f1729 100%)',
              border: '1px solid rgba(255,255,255,0.06)', borderRadius: '20px',
              padding: '24px', transition: 'all 0.2s',
              cursor: 'pointer', display: 'flex', flexDirection: 'column'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = strategy.color
              e.currentTarget.style.transform = 'translateY(-2px)'
              e.currentTarget.style.boxShadow = `0 8px 30px ${strategy.color}15`
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)'
              e.currentTarget.style.transform = 'none'
              e.currentTarget.style.boxShadow = 'none'
            }}
            onClick={() => navigate('/bots/create', { state: { strategy: strategy.id } })}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '16px' }}>
              <div style={{
                width: '40px', height: '40px', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: `${strategy.color}15`, color: strategy.color, border: `1px solid ${strategy.color}30`
              }}>
                <strategy.icon size={20} strokeWidth={2} />
              </div>
              <div>
                <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'white' }}>{strategy.name}</h3>
                <div style={{ display: 'flex', gap: '6px', marginTop: '4px' }}>
                  {strategy.tags.map(tag => (
                    <span key={tag} style={{
                      fontSize: '9px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em',
                      background: 'rgba(255,255,255,0.05)', color: '#94a3b8', padding: '2px 6px', borderRadius: '4px'
                    }}>
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            <p style={{ fontSize: '13px', color: '#cbd5e1', lineHeight: 1.5, flex: 1, marginBottom: '24px' }}>
              {strategy.description}
            </p>

            <div style={{ padding: '12px 16px', background: 'rgba(0,0,0,0.2)', borderRadius: '12px', display: 'flex', justifyContent: 'space-between' }}>
              <div>
                <p style={{ fontSize: '10px', fontWeight: 600, color: '#64748b', marginBottom: '4px' }}>HISTORICAL WIN RATE</p>
                <p style={{ fontSize: '15px', fontWeight: 700, color: 'white' }}>{strategy.stats.winRate}</p>
              </div>
              <div style={{ textAlign: 'right' }}>
                <p style={{ fontSize: '10px', fontWeight: 600, color: '#64748b', marginBottom: '4px' }}>PROFIT FACTOR</p>
                <p style={{ fontSize: '15px', fontWeight: 700, color: 'white' }}>{strategy.stats.profitFactor}</p>
              </div>
            </div>
            
            <button
              style={{
                marginTop: '16px', width: '100%', padding: '12px', borderRadius: '12px',
                background: `${strategy.color}15`, color: strategy.color, border: `1px solid ${strategy.color}40`,
                fontSize: '13px', fontWeight: 700, transition: 'all 0.2s', textAlign: 'center'
              }}
            >
              Deploy Bot Variant →
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
