import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useCreateBot } from '../api/bots'
import toast from 'react-hot-toast'
import { ArrowLeft, Rocket, Settings2, ShieldAlert } from 'lucide-react'

const ASSETS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'AVAX/USDT']
const STRATEGIES = {
  '11111111-1111-4111-8111-111111111111': { name: 'EMA Crossover', params: { fast_ema: 12, slow_ema: 26 } },
  '22222222-2222-4222-8222-222222222222': { name: 'RSI Divergence', params: { rsi_period: 14, overbought: 70, oversold: 30 } },
  '33333333-3333-4333-8333-333333333333': { name: 'Bollinger Mean Reversion', params: { length: 20, mult: 2.0 } },
  '44444444-4444-4444-8444-444444444444': { name: 'Momentum Breakout', params: { lookback: 20, threshold: 1.5 } },
}

export default function CreateBotPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { mutate: createBot, isPending } = useCreateBot()

  const defaultState = location.state || {}

  const [asset, setAsset] = useState(defaultState.symbol || ASSETS[0])
  const [isTestnet, setIsTestnet] = useState(true)
  const [strategyId, setStrategyId] = useState(defaultState.strategy || Object.keys(STRATEGIES)[0])
  const [parameters, setParameters] = useState(defaultState.parameters || STRATEGIES[strategyId || Object.keys(STRATEGIES)[0]].params)
  
  const [takeProfit, setTakeProfit] = useState('')
  const [stopLoss, setStopLoss] = useState('')

  useEffect(() => {
    // If not using pre-filled params, reset params when strategy changes
    if (!defaultState.parameters || defaultState.strategy !== strategyId) {
      setParameters(STRATEGIES[strategyId]?.params || {})
    }
  }, [strategyId, defaultState])

  const handleParamChange = (key, value) => {
    setParameters((prev) => ({ ...prev, [key]: Number(value) }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    
    const payload = {
      symbol: asset,
      is_testnet: isTestnet,
      strategy_id: strategyId,
      parameters,
      take_profit: takeProfit ? Number(takeProfit) : null,
      stop_loss: stopLoss ? Number(stopLoss) : null,
    }

    const idempotencyKey = crypto.randomUUID()

    createBot({ payload, idempotencyKey }, {
      onSuccess: () => {
        toast.success('Live bot deployed successfully!')
        navigate('/bots/dashboard')
      },
      onError: (err) => {
        toast.error(err.response?.data?.detail || 'Failed to deploy bot')
      }
    })
  }

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '32px 28px' }}>
      
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '32px' }}>
        <button
          onClick={() => navigate(-1)}
          style={{
            width: '40px', height: '40px', borderRadius: '12px',
            background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b',
            cursor: 'pointer', transition: 'all 0.2s'
          }}
          onMouseEnter={(e) => { e.currentTarget.style.color = 'white'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.15)' }}
          onMouseLeave={(e) => { e.currentTarget.style.color = '#64748b'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)' }}
        >
          <ArrowLeft size={18} />
        </button>
        <div>
          <h1 style={{ fontSize: '24px', fontWeight: 700, color: 'white' }}>Deploy Live Bot</h1>
          <p style={{ fontSize: '13px', color: '#64748b', marginTop: '4px' }}>Configure and launch your automated trading algorithm.</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        
        {/* Environment Toggle */}
        <div style={{ display: 'flex', gap: '12px', padding: '6px', background: 'rgba(0,0,0,0.2)', borderRadius: '14px', width: 'fit-content' }}>
          <button
            type="button"
            onClick={() => setIsTestnet(true)}
            style={{
              padding: '10px 24px', borderRadius: '10px', fontSize: '13px', fontWeight: 600,
              background: isTestnet ? 'rgba(129,140,248,0.15)' : 'transparent',
              color: isTestnet ? '#818cf8' : '#64748b',
              border: isTestnet ? '1px solid rgba(129,140,248,0.3)' : '1px solid transparent',
              cursor: 'pointer', transition: 'all 0.2s'
            }}
          >
            Testnet (Paper)
          </button>
          <button
            type="button"
            onClick={() => setIsTestnet(false)}
            style={{
              padding: '10px 24px', borderRadius: '10px', fontSize: '13px', fontWeight: 600,
              background: !isTestnet ? 'rgba(244,63,94,0.15)' : 'transparent',
              color: !isTestnet ? '#f43f5e' : '#64748b',
              border: !isTestnet ? '1px solid rgba(244,63,94,0.3)' : '1px solid transparent',
              cursor: 'pointer', transition: 'all 0.2s'
            }}
          >
            Mainnet (Live)
          </button>
        </div>

        <div style={{ background: 'linear-gradient(145deg,#131b2f,#0f1729)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '20px', padding: '24px' }}>
          <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'white', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Settings2 size={16} style={{ color: '#818cf8' }}/> 
            Core Settings
          </h3>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) minmax(0,1fr)', gap: '20px' }}>
            {/* Asset */}
            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 500, color: '#94a3b8', marginBottom: '8px' }}>Asset Pair</label>
              <select
                value={asset}
                onChange={(e) => setAsset(e.target.value)}
                style={{
                  width: '100%', padding: '12px 14px', borderRadius: '12px',
                  background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.1)',
                  color: 'white', fontSize: '14px', outline: 'none'
                }}
              >
                {ASSETS.map(a => <option key={a} value={a} style={{ background: '#0f1729' }}>{a}</option>)}
              </select>
            </div>

            {/* Strategy */}
            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 500, color: '#94a3b8', marginBottom: '8px' }}>Strategy Template</label>
              <select
                value={strategyId}
                onChange={(e) => setStrategyId(e.target.value)}
                style={{
                  width: '100%', padding: '12px 14px', borderRadius: '12px',
                  background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.1)',
                  color: 'white', fontSize: '14px', outline: 'none'
                }}
              >
                {Object.entries(STRATEGIES).map(([id, s]) => (
                  <option key={id} value={id} style={{ background: '#0f1729' }}>{s.name}</option>
                ))}
                {/* Support custom strategy injected via state */}
                {!STRATEGIES[strategyId] && (
                  <option value={strategyId} style={{ background: '#0f1729' }}>{strategyId} (Custom)</option>
                )}
              </select>
            </div>
          </div>

          {/* Dynamic Parameters */}
          {Object.keys(parameters).length > 0 && (
            <div style={{ marginTop: '24px', paddingTop: '24px', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 500, color: '#94a3b8', marginBottom: '12px' }}>Strategy Parameters</label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '16px' }}>
                {Object.entries(parameters).map(([key, val]) => (
                  <div key={key}>
                    <p style={{ fontSize: '11px', color: '#64748b', marginBottom: '6px', textTransform: 'uppercase' }}>{key.replace(/_/g, ' ')}</p>
                    <input
                      type="number"
                      value={val}
                      onChange={(e) => handleParamChange(key, e.target.value)}
                      style={{
                        width: '100%', padding: '10px 14px', borderRadius: '10px',
                        background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.1)',
                        color: 'white', fontSize: '14px', outline: 'none'
                      }}
                      required
                    />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div style={{ background: 'linear-gradient(145deg,#131b2f,#0f1729)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '20px', padding: '24px' }}>
          <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'white', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <ShieldAlert size={16} style={{ color: '#f59e0b' }}/> 
            Risk Management (Circuit Breakers)
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) minmax(0,1fr)', gap: '20px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 500, color: '#94a3b8', marginBottom: '8px' }}>Daily Take Profit ($)</label>
              <input
                type="number"
                placeholder="Upper Bound PnL (e.g. 500)"
                value={takeProfit}
                onChange={(e) => setTakeProfit(e.target.value)}
                style={{
                  width: '100%', padding: '12px 14px', borderRadius: '12px',
                  background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(16,185,129,0.2)',
                  color: 'white', fontSize: '14px', outline: 'none'
                }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 500, color: '#94a3b8', marginBottom: '8px' }}>Daily Stop Loss ($)</label>
              <input
                type="number"
                placeholder="Lower Bound PnL (e.g. -200)"
                value={stopLoss}
                onChange={(e) => setStopLoss(e.target.value)}
                style={{
                  width: '100%', padding: '12px 14px', borderRadius: '12px',
                  background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(244,63,94,0.2)',
                  color: 'white', fontSize: '14px', outline: 'none'
                }}
              />
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '8px' }}>
          <button
            type="submit"
            disabled={isPending}
            style={{
              display: 'flex', alignItems: 'center', gap: '8px',
              padding: '14px 28px', borderRadius: '14px',
              background: 'linear-gradient(135deg, #818cf8 0%, #6366f1 100%)',
              border: 'none', color: 'white', fontSize: '15px', fontWeight: 700,
              cursor: 'pointer', transition: 'all 0.2s',
              boxShadow: '0 4px 24px rgba(99,102,241,0.4)',
              opacity: isPending ? 0.7 : 1
            }}
          >
            <Rocket size={18} />
            {isPending ? 'Deploying...' : 'Launch Bot'}
          </button>
        </div>
      </form>
    </div>
  )
}
