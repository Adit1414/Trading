import { useState, useMemo } from 'react'
import { useStrategies } from '../api/strategies'
import { useRunBacktest } from '../api/backtests'
import { Play, X } from 'lucide-react'
import toast from 'react-hot-toast'

// ── Shared field styles ────────────────────────────────────────────
const S = {
  input: {
    width:'100%', padding:'10px 14px',
    background:'rgba(0,0,0,0.3)', border:'1px solid rgba(255,255,255,0.07)',
    borderRadius:'10px', fontSize:'13px', color:'white',
    outline:'none', transition:'all 0.2s', boxSizing:'border-box', fontFamily:'inherit',
  },
  label: {
    display:'block', fontSize:'10px', fontWeight:700, color:'#475569',
    letterSpacing:'0.1em', textTransform:'uppercase', marginBottom:'6px',
  },
}

function Field({ label, children, hint }) {
  return (
    <div>
      <label style={S.label}>{label}</label>
      {children}
      {hint && <p style={{ fontSize:'10px', color:'#334155', marginTop:'4px' }}>{hint}</p>}
    </div>
  )
}

function StyledInput({ style, ...props }) {
  return (
    <input
      {...props}
      style={{ ...S.input, ...style }}
      onFocus={(e) => { e.target.style.borderColor='rgba(129,140,248,0.45)'; e.target.style.boxShadow='0 0 0 3px rgba(129,140,248,0.08)' }}
      onBlur={(e)  => { e.target.style.borderColor='rgba(255,255,255,0.07)'; e.target.style.boxShadow='none' }}
    />
  )
}

function StyledSelect({ style, ...props }) {
  return (
    <select
      {...props}
      style={{ ...S.input, cursor:'pointer', ...style }}
      onFocus={(e) => { e.target.style.borderColor='rgba(129,140,248,0.45)' }}
      onBlur={(e)  => { e.target.style.borderColor='rgba(255,255,255,0.07)' }}
    />
  )
}

export default function BacktestForm({ onClose }) {
  const { data: strategies, isLoading: strategiesLoading } = useStrategies()
  const runBacktest = useRunBacktest()

  const [selectedStrategyId, setSelectedStrategyId] = useState('')
  const [name,          setName]          = useState('')
  const [symbol,        setSymbol]        = useState('BTCUSDT')
  const [contractType,  setContractType]  = useState('SPOT')
  const [interval,      setInterval_]     = useState('1d')
  const [initialCash,   setInitialCash]   = useState(100000)
  const [commission,    setCommission]    = useState(0.001)
  const [slippage,      setSlippage]      = useState(0.0005)
  const [orderSizeMode, setOrderSizeMode] = useState('PCT_EQUITY')
  const [orderSizePct,  setOrderSizePct]  = useState(100)
  const [orderSizeUsdt, setOrderSizeUsdt] = useState(10)
  const [intraday,      setIntraday]      = useState(false)
  const [startDate,     setStartDate]     = useState('2024-01-01')
  const [endDate,       setEndDate]       = useState('2024-06-30')
  const [tradingMarket, setTradingMarket] = useState('BINANCE')
  const [strategyConfigJson,   setStrategyConfigJson]   = useState('{}')
  const [strategyConfigValues, setStrategyConfigValues] = useState({})

  const selectedStrategy = useMemo(
    () => strategies?.find((s) => s.id === selectedStrategyId),
    [strategies, selectedStrategyId]
  )

  const parameterSchema = selectedStrategy?.parameter_schema
  const hasValidSchema  = Object.keys(parameterSchema?.properties || {}).length > 0

  const handleStrategyChange = (id) => {
    setSelectedStrategyId(id)
    const strat = strategies?.find((s) => s.id === id)
    if (strat?.parameter_schema?.properties) {
      const defaults = {}
      for (const [key, prop] of Object.entries(strat.parameter_schema.properties)) {
        if (prop.default !== undefined) defaults[key] = prop.default
      }
      setStrategyConfigValues(defaults)
      setStrategyConfigJson(JSON.stringify(defaults, null, 2))
    } else {
      setStrategyConfigValues({})
      setStrategyConfigJson('{}')
    }
  }

  const updateConfigField = (key, value, type) => {
    setStrategyConfigValues((prev) => {
      const u = { ...prev }
      u[key] = (type === 'number' || type === 'integer') ? (value === '' ? '' : Number(value)) : value
      return u
    })
  }

  const resolveSchemaProps = (schema) => {
    if (!schema) return {}
    if (schema.properties) return schema.properties
    if (schema.allOf) { let m = {}; for (const s of schema.allOf) if (s.properties) m = { ...m, ...s.properties }; return m }
    return {}
  }
  const resolvedProps = resolveSchemaProps(parameterSchema)

  const renderSchemaField = (key, prop) => {
    const value = strategyConfigValues[key] ?? prop.default ?? ''
    const label = prop.title || key.replace(/_/g, ' ')
    if (prop.enum) return (
      <Field key={key} label={label} hint={prop.description}>
        <StyledSelect value={value} onChange={(e) => updateConfigField(key, e.target.value, 'string')}>
          {prop.enum.map((o) => <option key={o} value={o}>{o}</option>)}
        </StyledSelect>
      </Field>
    )
    if (prop.type === 'number' || prop.type === 'integer') return (
      <Field key={key} label={`${label}${prop.minimum !== undefined && prop.maximum !== undefined ? ` (${prop.minimum}–${prop.maximum})` : ''}`} hint={prop.description}>
        <StyledInput type="number" value={value} min={prop.minimum} max={prop.maximum} step={prop.type === 'integer' ? 1 : 'any'} onChange={(e) => updateConfigField(key, e.target.value, prop.type)} />
      </Field>
    )
    return (
      <Field key={key} label={label} hint={prop.description}>
        <StyledInput type="text" value={value} onChange={(e) => updateConfigField(key, e.target.value, 'string')} />
      </Field>
    )
  }

  const intervals = [
    { value:'1m',label:'1 min' },{ value:'3m',label:'3 min' },{ value:'5m',label:'5 min' },
    { value:'15m',label:'15 min' },{ value:'30m',label:'30 min' },{ value:'1h',label:'1 hour' },
    { value:'2h',label:'2 hours' },{ value:'4h',label:'4 hours' },{ value:'6h',label:'6 hours' },
    { value:'8h',label:'8 hours' },{ value:'12h',label:'12 hours' },{ value:'1d',label:'1 day' },
    { value:'3d',label:'3 days' },{ value:'1w',label:'1 week' },{ value:'1M',label:'1 month' },
  ]

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!selectedStrategy) { toast.error('Please select a strategy.'); return }
    if (!name.trim())       { toast.error('Please enter a backtest name.'); return }
    let configToSend = {}
    if (hasValidSchema || Object.keys(resolvedProps).length > 0) {
      configToSend = { ...strategyConfigValues }
    } else {
      try { configToSend = JSON.parse(strategyConfigJson) }
      catch { toast.error('Invalid JSON in strategy config.'); return }
    }
    const payload = {
      strategy: selectedStrategy.type_code,
      strategy_config: configToSend,
      name: name.trim(),
      symbol: symbol.toUpperCase(),
      contract_type: contractType,
      trading_market: 'BINANCE',
      interval, initial_cash: Number(initialCash),
      commission: Number(commission), slippage: Number(slippage),
      order_size_mode: orderSizeMode, order_size_pct: Number(orderSizePct),
      intraday, start_date: startDate, end_date: endDate,
    }
    if (orderSizeMode === 'FIXED_USDT') payload.order_size_usdt = Number(orderSizeUsdt)
    runBacktest.mutate(payload, {
      onSuccess: (data) => { toast.success(`Backtest "${data.name}" started!`); onClose?.() },
      onError: (err) => { console.error('[BacktestForm] Error:', err) },
    })
  }

  return (
    <div style={{ position:'fixed', inset:0, zIndex:50, display:'flex', alignItems:'center', justifyContent:'center', padding:'16px', background:'rgba(0,0,0,0.75)', backdropFilter:'blur(10px)', WebkitBackdropFilter:'blur(10px)' }}>
      <div style={{
        background:'linear-gradient(145deg,#131b2f 0%,#0f1729 100%)',
        border:'1px solid rgba(255,255,255,0.08)', borderRadius:'22px',
        width:'100%', maxWidth:'820px', maxHeight:'90vh', overflowY:'auto',
        boxShadow:'0 32px 80px rgba(0,0,0,0.7)',
      }}>
        {/* Header */}
        <div style={{
          display:'flex', alignItems:'center', justifyContent:'space-between',
          padding:'22px 28px', borderBottom:'1px solid rgba(255,255,255,0.06)',
          position:'sticky', top:0, zIndex:10,
          background:'rgba(15,23,41,0.95)', backdropFilter:'blur(12px)',
          WebkitBackdropFilter:'blur(12px)', borderRadius:'22px 22px 0 0',
        }}>
          <div style={{ display:'flex', alignItems:'center', gap:'12px' }}>
            <div style={{ width:'34px', height:'34px', borderRadius:'10px', background:'rgba(129,140,248,0.12)', border:'1px solid rgba(129,140,248,0.2)', display:'flex', alignItems:'center', justifyContent:'center' }}>
              <Play size={16} style={{ color:'#818cf8' }} strokeWidth={2} />
            </div>
            <h2 style={{ fontSize:'17px', fontWeight:700, color:'white', letterSpacing:'-0.01em' }}>
              Start New Backtest
            </h2>
          </div>
          <button
            onClick={onClose}
            style={{ width:'32px', height:'32px', borderRadius:'9px', display:'flex', alignItems:'center', justifyContent:'center', border:'1px solid transparent', background:'transparent', color:'#475569', cursor:'pointer', transition:'all 0.2s' }}
            onMouseEnter={(e) => { e.currentTarget.style.background='rgba(255,255,255,0.06)'; e.currentTarget.style.color='white' }}
            onMouseLeave={(e) => { e.currentTarget.style.background='transparent'; e.currentTarget.style.color='#475569' }}
          >
            <X size={18} strokeWidth={2} />
          </button>
        </div>

        {/* Form body */}
        <form onSubmit={handleSubmit} style={{ padding:'24px 28px', display:'flex', flexDirection:'column', gap:'20px' }}>

          {/* Row 1: Strategy + Config */}
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'16px' }}>
            <Field label={`Strategy ${strategies?.length ? `· ${strategies.length} available` : ''}`}>
              {strategiesLoading
                ? <div style={{ ...S.input, color:'#475569' }}>Loading strategies…</div>
                : <StyledSelect value={selectedStrategyId} onChange={(e) => handleStrategyChange(e.target.value)} required>
                    <option value="">Select strategy</option>
                    {strategies?.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                  </StyledSelect>
              }
            </Field>
            <Field label="Strategy Configuration">
              <StyledSelect>
                <option value="">Select configuration</option>
                <option value="custom">Custom (Below)</option>
              </StyledSelect>
            </Field>
          </div>

          {/* Strategy params */}
          {selectedStrategy && (
            <div style={{ padding:'16px', borderRadius:'14px', background:'rgba(0,0,0,0.2)', border:'1px solid rgba(255,255,255,0.06)' }}>
              <p style={{ fontSize:'12px', fontWeight:600, color:'#94a3b8', marginBottom:'14px' }}>
                Parameters for <span style={{ color:'white' }}>{selectedStrategy.name}</span>
              </p>
              {Object.keys(resolvedProps).length > 0 ? (
                <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(180px,1fr))', gap:'12px' }}>
                  {Object.entries(resolvedProps).filter(([k]) => k !== 'title' && k !== 'type').map(([k, p]) => renderSchemaField(k, p))}
                </div>
              ) : (
                <textarea value={strategyConfigJson} onChange={(e) => setStrategyConfigJson(e.target.value)} rows={3}
                  style={{ ...S.input, fontFamily:'monospace', fontSize:'12px', resize:'vertical' }}
                />
              )}
            </div>
          )}

          {/* Row 2: Name + Symbol */}
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'16px' }}>
            <Field label="Backtest Name">
              <StyledInput type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. MACD Test Run 1" required />
            </Field>
            <Field label="Symbol">
              <StyledInput type="text" value={symbol} onChange={(e) => setSymbol(e.target.value)} placeholder="BTCUSDT" required />
            </Field>
          </div>

          {/* Row 3: Contract + Market */}
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'16px' }}>
            <Field label="Contract Type">
              <StyledSelect value={contractType} onChange={(e) => setContractType(e.target.value)}>
                <option value="SPOT">SPOT</option>
                <option value="FUTURE">FUTURE</option>
              </StyledSelect>
            </Field>
            <Field label="Trading Market">
              <StyledInput type="text" value={tradingMarket} onChange={(e) => setTradingMarket(e.target.value)} placeholder="NSE" required />
            </Field>
          </div>

          {/* Row 4: 4-col numeric */}
          <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:'12px' }}>
            <Field label="Initial Cash ($)">
              <div style={{ position:'relative' }}>
                <span style={{ position:'absolute', left:'12px', top:'50%', transform:'translateY(-50%)', color:'#475569', fontSize:'13px', pointerEvents:'none' }}>$</span>
                <StyledInput type="number" value={initialCash} onChange={(e) => setInitialCash(e.target.value)} style={{ paddingLeft:'26px' }} />
              </div>
            </Field>
            <Field label="Commission">
              <StyledInput type="number" value={commission} onChange={(e) => setCommission(e.target.value)} step="0.0001" />
            </Field>
            <Field label={`Quantity (${orderSizeMode === 'PCT_EQUITY' ? '%' : 'USDT'})`}>
              <StyledInput type="number"
                value={orderSizeMode === 'PCT_EQUITY' ? orderSizePct : orderSizeUsdt}
                onChange={(e) => orderSizeMode === 'PCT_EQUITY' ? setOrderSizePct(e.target.value) : setOrderSizeUsdt(e.target.value)}
              />
            </Field>
            <Field label="Spread">
              <StyledInput type="number" value={slippage} onChange={(e) => setSlippage(e.target.value)} step="0.0001" />
            </Field>
          </div>

          {/* Row 5: Order mode + interval + dates */}
          <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:'12px' }}>
            <Field label="Order Mode">
              <StyledSelect value={orderSizeMode} onChange={(e) => setOrderSizeMode(e.target.value)}>
                <option value="FIXED_USDT">Fixed Size</option>
                <option value="PCT_EQUITY">% of Equity</option>
              </StyledSelect>
            </Field>
            <Field label="Interval">
              <StyledSelect value={interval} onChange={(e) => setInterval_(e.target.value)}>
                {intervals.map((i) => <option key={i.value} value={i.value}>{i.label}</option>)}
              </StyledSelect>
            </Field>
            <Field label="Start Date">
              <StyledInput type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
            </Field>
            <Field label="End Date">
              <StyledInput type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
            </Field>
          </div>

          {/* Intraday toggle */}
          <div
            onClick={() => setIntraday(!intraday)}
            style={{
              display:'flex', alignItems:'center', justifyContent:'space-between',
              padding:'14px 16px', borderRadius:'12px', cursor:'pointer',
              background:'rgba(0,0,0,0.2)', border:'1px solid rgba(255,255,255,0.06)',
              transition:'border-color 0.2s',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.borderColor='rgba(255,255,255,0.1)' }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor='rgba(255,255,255,0.06)' }}
          >
            <div>
              <p style={{ fontSize:'13px', fontWeight:600, color:'white', marginBottom:'2px' }}>Intraday Trading</p>
              <p style={{ fontSize:'11px', color:'#475569' }}>Enable for same-day open/close trades only</p>
            </div>
            {/* Toggle pill */}
            <div style={{
              width:'44px', height:'24px', borderRadius:'12px', padding:'2px',
              display:'flex', alignItems:'center', transition:'background 0.25s',
              background: intraday ? '#818cf8' : '#1e293b',
              flexShrink:0, marginLeft:'16px',
            }}>
              <div style={{
                width:'20px', height:'20px', borderRadius:'50%', background:'white',
                boxShadow:'0 1px 4px rgba(0,0,0,0.3)',
                transition:'transform 0.25s cubic-bezier(0.4,0,0.2,1)',
                transform: intraday ? 'translateX(20px)' : 'translateX(0)',
              }} />
            </div>
          </div>

          {/* Footer actions */}
          <div style={{ display:'flex', justifyContent:'flex-end', alignItems:'center', gap:'12px', paddingTop:'4px', borderTop:'1px solid rgba(255,255,255,0.05)' }}>
            <button
              type="button" onClick={onClose}
              style={{ fontSize:'13px', fontWeight:600, color:'#475569', background:'none', border:'none', cursor:'pointer', padding:'8px', transition:'color 0.2s', fontFamily:'inherit' }}
              onMouseEnter={(e) => { e.currentTarget.style.color='#94a3b8' }}
              onMouseLeave={(e) => { e.currentTarget.style.color='#475569' }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={runBacktest.isPending}
              style={{
                display:'flex', alignItems:'center', gap:'8px',
                padding:'10px 22px', borderRadius:'12px',
                background:'linear-gradient(135deg,#818cf8 0%,#6366f1 100%)',
                border:'none', color:'white',
                fontSize:'13px', fontWeight:700, cursor: runBacktest.isPending ? 'not-allowed' : 'pointer',
                opacity: runBacktest.isPending ? 0.6 : 1,
                boxShadow:'0 4px 18px rgba(99,102,241,0.4)',
                transition:'all 0.2s', fontFamily:'inherit',
              }}
              onMouseEnter={(e) => { if (!runBacktest.isPending) e.currentTarget.style.opacity='0.88' }}
              onMouseLeave={(e) => { e.currentTarget.style.opacity = runBacktest.isPending ? '0.6' : '1' }}
            >
              <Play size={15} strokeWidth={2.5} />
              {runBacktest.isPending ? 'Running…' : 'Start Simulation'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}