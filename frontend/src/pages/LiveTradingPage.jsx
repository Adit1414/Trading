import { useState, useEffect, useRef, useCallback } from 'react'
import {
  TrendingUp, TrendingDown, Activity, Zap, RefreshCw,
  ArrowUpRight, ArrowDownRight, ChevronDown, AlertTriangle,
  Plus, Minus, BarChart2, List, Clock, Wallet,
  Target, Shield, X, CheckCircle, Circle,
} from 'lucide-react'
import toast from 'react-hot-toast'

/* ─── Simulated market data ───────────────────────────────────────────── */
const ASSETS = [
  { symbol: 'BTC/USDT', base: 'BTC', price: 64230, change: 2.4,  volume: '1.24B', high: 65100, low: 63500 },
  { symbol: 'ETH/USDT', base: 'ETH', price: 3450,  change: -1.2, volume: '458M',  high: 3520,  low: 3380  },
  { symbol: 'SOL/USDT', base: 'SOL', price: 145.2, change: 5.7,  volume: '92M',   high: 149.0, low: 137.5 },
  { symbol: 'BNB/USDT', base: 'BNB', price: 590,   change: 0.8,  volume: '74M',   high: 595,   low: 580   },
  { symbol: 'AVAX/USDT',base: 'AVAX',price: 36.4,  change: -2.1, volume: '31M',   high: 37.8,  low: 35.0  },
]

/* generate deterministic sparkline points */
function generateChart(basePrice, points = 80) {
  const arr = []
  let p = basePrice * 0.98
  for (let i = 0; i < points; i++) {
    p += (Math.random() - 0.48) * basePrice * 0.003
    arr.push(parseFloat(p.toFixed(2)))
  }
  arr[arr.length - 1] = basePrice
  return arr
}

/* generate order book levels */
function generateBook(mid, side, levels = 12) {
  return Array.from({ length: levels }, (_, i) => {
    const offset = (i + 1) * mid * 0.0003 * (0.5 + Math.random())
    const price  = side === 'ask' ? mid + offset : mid - offset
    const size   = parseFloat((Math.random() * 2 + 0.05).toFixed(4))
    const total  = parseFloat((price * size).toFixed(2))
    return { price: parseFloat(price.toFixed(2)), size, total }
  }).sort((a, b) => side === 'ask' ? a.price - b.price : b.price - a.price)
}

/* generate mock recent trades */
function generateTrades(mid, n = 20) {
  return Array.from({ length: n }, (_, i) => ({
    id: i,
    price: parseFloat((mid + (Math.random() - 0.5) * mid * 0.002).toFixed(2)),
    size:  parseFloat((Math.random() * 1.5 + 0.01).toFixed(4)),
    side:  Math.random() > 0.5 ? 'BUY' : 'SELL',
    time:  `${String(Math.floor(Math.random() * 60)).padStart(2,'0')}s ago`,
  }))
}

/* ─── Tiny canvas sparkline ───────────────────────────────────────────── */
function Sparkline({ data, color, height = 280, fullWidth = false }) {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !data.length) return
    const ctx = canvas.getContext('2d')
    const W = canvas.width
    const H = canvas.height
    const min = Math.min(...data)
    const max = Math.max(...data)
    const range = max - min || 1

    ctx.clearRect(0, 0, W, H)

    const pts = data.map((v, i) => ({
      x: (i / (data.length - 1)) * W,
      y: H - ((v - min) / range) * (H - 20) - 10,
    }))

    /* gradient fill */
    const grad = ctx.createLinearGradient(0, 0, 0, H)
    grad.addColorStop(0, color + '40')
    grad.addColorStop(1, color + '00')

    ctx.beginPath()
    ctx.moveTo(pts[0].x, pts[0].y)
    pts.forEach((p, i) => {
      if (i === 0) return
      const cp = pts[i - 1]
      const mx = (cp.x + p.x) / 2
      ctx.bezierCurveTo(mx, cp.y, mx, p.y, p.x, p.y)
    })
    ctx.lineTo(W, H)
    ctx.lineTo(0, H)
    ctx.closePath()
    ctx.fillStyle = grad
    ctx.fill()

    /* line */
    ctx.beginPath()
    ctx.moveTo(pts[0].x, pts[0].y)
    pts.forEach((p, i) => {
      if (i === 0) return
      const cp = pts[i - 1]
      const mx = (cp.x + p.x) / 2
      ctx.bezierCurveTo(mx, cp.y, mx, p.y, p.x, p.y)
    })
    ctx.strokeStyle = color
    ctx.lineWidth = 2
    ctx.stroke()

    /* last point dot */
    const last = pts[pts.length - 1]
    ctx.beginPath()
    ctx.arc(last.x, last.y, 4, 0, Math.PI * 2)
    ctx.fillStyle = color
    ctx.fill()
    ctx.strokeStyle = '#0b1221'
    ctx.lineWidth = 2
    ctx.stroke()
  }, [data, color])

  return (
    <canvas
      ref={canvasRef}
      width={fullWidth ? 900 : 600}
      height={height}
      style={{ width: '100%', height: `${height}px`, display: 'block' }}
    />
  )
}

/* ─── Depth Bar (order book visual) ─────────────────────────────────── */
function DepthBar({ value, max, side }) {
  const pct = Math.min((value / max) * 100, 100)
  return (
    <div style={{ position: 'absolute', top: 0, bottom: 0, width: `${pct}%`,
      [side === 'bid' ? 'left' : 'right']: 0,
      background: side === 'bid' ? 'rgba(16,185,129,0.08)' : 'rgba(244,63,94,0.08)',
      transition: 'width 0.4s ease',
    }} />
  )
}

/* ─── Shared card wrapper ─────────────────────────────────────────────── */
function Panel({ children, style = {} }) {
  return (
    <div style={{
      background: 'linear-gradient(145deg,#131b2f 0%,#0f1729 100%)',
      border: '1px solid rgba(255,255,255,0.06)',
      borderRadius: '18px',
      overflow: 'hidden',
      boxShadow: '0 4px 24px rgba(0,0,0,0.25)',
      ...style,
    }}>
      {children}
    </div>
  )
}

function PanelHeader({ children, style = {} }) {
  return (
    <div style={{
      padding: '14px 18px',
      borderBottom: '1px solid rgba(255,255,255,0.05)',
      display: 'flex', alignItems: 'center', gap: '10px',
      ...style,
    }}>
      {children}
    </div>
  )
}

/* ════════════════════════════════════════════════════════════════════════
   MAIN PAGE
═══════════════════════════════════════════════════════════════════════ */
export default function LiveTradingPage() {
  /* ── Asset state ── */
  const [asset, setAsset]         = useState(ASSETS[0])
  const [assetOpen, setAssetOpen] = useState(false)
  const [livePrice, setLivePrice] = useState(asset.price)
  const [chartData, setChartData] = useState(() => generateChart(asset.price))
  const [asks, setAsks]           = useState(() => generateBook(asset.price, 'ask'))
  const [bids, setBids]           = useState(() => generateBook(asset.price, 'bid'))
  const [trades, setTrades]       = useState(() => generateTrades(asset.price))
  const [bookTab, setBookTab]     = useState('book') // 'book' | 'trades'

  /* ── Order form ── */
  const [orderSide, setOrderSide]   = useState('buy')
  const [orderType, setOrderType]   = useState('market')
  const [orderAmount, setOrderAmount] = useState('')
  const [limitPrice, setLimitPrice]   = useState('')
  const [orderPct, setOrderPct]       = useState(null)
  const [placing, setPlacing]         = useState(false)

  /* ── Wallet / Positions ── */
  const [balance] = useState({ usdt: 12450.80, btc: 0.1842 })
  const [positions, setPositions] = useState([
    { id: 1, pair: 'BTC/USDT', side: 'LONG',  size: 0.05, entry: 62800, liq: 58000, pnl: '+$71.50',  pnlPct: '+2.28%', isWin: true  },
    { id: 2, pair: 'ETH/USDT', side: 'SHORT', size: 0.80, entry: 3500,  liq: 3780,  pnl: '-$40.00',  pnlPct: '-1.43%', isWin: false },
  ])
  const [openOrders, setOpenOrders] = useState([
    { id: 3, pair: 'SOL/USDT', type: 'LIMIT', side: 'BUY',  price: 138.0, size: 2.0,  status: 'Open' },
    { id: 4, pair: 'BNB/USDT', type: 'LIMIT', side: 'SELL', price: 598.0, size: 0.5,  status: 'Open' },
  ])
  const [posTab, setPosTab] = useState('positions') // 'positions' | 'orders' | 'history'

  /* timeframe tabs */
  const [tf, setTf] = useState('1H')

  /* ── Simulated live tick ── */
  useEffect(() => {
    const interval = setInterval(() => {
      setLivePrice((prev) => {
        const next = parseFloat((prev + (Math.random() - 0.48) * prev * 0.0015).toFixed(2))
        setChartData((d) => [...d.slice(1), next])
        setAsks(generateBook(next, 'ask'))
        setBids(generateBook(next, 'bid'))
        setTrades((t) => [
          { id: Date.now(), price: next, size: parseFloat((Math.random() * 0.5 + 0.01).toFixed(4)),
            side: Math.random() > 0.5 ? 'BUY' : 'SELL', time: 'just now' },
          ...t.slice(0, 19),
        ])
        return next
      })
    }, 1800)
    return () => clearInterval(interval)
  }, [])

  /* ── Switch asset ── */
  const switchAsset = (a) => {
    setAsset(a)
    setLivePrice(a.price)
    setChartData(generateChart(a.price))
    setAsks(generateBook(a.price, 'ask'))
    setBids(generateBook(a.price, 'bid'))
    setTrades(generateTrades(a.price))
    setAssetOpen(false)
    setOrderAmount('')
    setLimitPrice('')
  }

  /* ── Place order ── */
  const placeOrder = async () => {
    if (!orderAmount || isNaN(Number(orderAmount)) || Number(orderAmount) <= 0) {
      toast.error('Enter a valid amount.')
      return
    }
    if (orderType === 'limit' && (!limitPrice || isNaN(Number(limitPrice)))) {
      toast.error('Enter a valid limit price.')
      return
    }
    setPlacing(true)
    await new Promise((r) => setTimeout(r, 900))
    const side = orderSide.toUpperCase()
    const type = orderType.toUpperCase()
    const price = orderType === 'market' ? livePrice : Number(limitPrice)

    if (orderType === 'market') {
      toast.success(`${side} order filled @ $${price.toLocaleString()}`)
      setPositions((prev) => [
        {
          id: Date.now(), pair: asset.symbol, side: side === 'BUY' ? 'LONG' : 'SHORT',
          size: Number(orderAmount), entry: price, liq: side === 'BUY' ? price * 0.9 : price * 1.1,
          pnl: '$0.00', pnlPct: '0.00%', isWin: true,
        },
        ...prev,
      ])
    } else {
      toast.success(`${side} limit order placed @ $${price.toLocaleString()}`)
      setOpenOrders((prev) => [
        { id: Date.now(), pair: asset.symbol, type: 'LIMIT', side, price, size: Number(orderAmount), status: 'Open' },
        ...prev,
      ])
    }
    setOrderAmount('')
    setLimitPrice('')
    setOrderPct(null)
    setPlacing(false)
    setPosTab(orderType === 'market' ? 'positions' : 'orders')
  }

  const cancelOrder = (id) => {
    setOpenOrders((prev) => prev.filter((o) => o.id !== id))
    toast.success('Order cancelled.')
  }
  const closePosition = (id) => {
    setPositions((prev) => prev.filter((p) => p.id !== id))
    toast.success('Position closed at market.')
  }

  const isUp   = livePrice >= asset.price * 0.999
  const color  = isUp ? '#10b981' : '#f43f5e'
  const maxAsk = Math.max(...asks.map((a) => a.size))
  const maxBid = Math.max(...bids.map((b) => b.size))

  const total = orderAmount && livePrice
    ? (Number(orderAmount) * (orderType === 'market' ? livePrice : (Number(limitPrice) || livePrice))).toFixed(2)
    : ''

  /* ── PCT helpers ── */
  const applyPct = (pct) => {
    setOrderPct(pct)
    const available = orderSide === 'buy' ? balance.usdt : balance[asset.base.toLowerCase()] ?? 0
    const price = orderType === 'market' ? livePrice : (Number(limitPrice) || livePrice)
    if (orderSide === 'buy') {
      setOrderAmount(((available * pct / 100) / price).toFixed(4))
    } else {
      setOrderAmount(((available * pct / 100)).toFixed(4))
    }
  }

  return (
    <div style={{ maxWidth: '1600px', margin: '0 auto', padding: '24px 24px 32px' }}>

      {/* ── Page header ── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px', gap: '16px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{
            width: '44px', height: '44px', borderRadius: '13px', flexShrink: 0,
            background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.25)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#10b981',
          }}>
            <Zap size={22} strokeWidth={2} />
          </div>
          <div>
            <h1 style={{ fontSize: '24px', fontWeight: 700, color: 'white', letterSpacing: '-0.02em', lineHeight: 1 }}>
              Live Trading
            </h1>
            <p style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>
              Real-time order execution · Simulated paper-trading mode active
            </p>
          </div>
        </div>

        {/* Live badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: '7px',
            padding: '7px 14px', borderRadius: '10px',
            background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.2)',
          }}>
            <span style={{
              width: '7px', height: '7px', borderRadius: '50%', background: '#10b981',
              boxShadow: '0 0 8px #10b981', animation: 'pulse-ring 2s ease-in-out infinite',
              display: 'inline-block',
            }} />
            <span style={{ fontSize: '12px', fontWeight: 700, color: '#10b981' }}>LIVE</span>
          </div>
          <div style={{
            padding: '7px 14px', borderRadius: '10px',
            background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)',
            fontSize: '11px', fontWeight: 700, color: '#f59e0b',
          }}>
            📄 Paper Mode
          </div>
        </div>
      </div>

      {/* ── Asset selector strip ── */}
      <Panel style={{ marginBottom: '16px', borderRadius: '14px' }}>
        <div style={{ padding: '14px 20px', display: 'flex', alignItems: 'center', gap: '24px', flexWrap: 'wrap' }}>

          {/* Asset picker */}
          <div style={{ position: 'relative' }}>
            <button
              id="asset-picker-btn"
              onClick={() => setAssetOpen((o) => !o)}
              style={{
                display: 'flex', alignItems: 'center', gap: '8px',
                padding: '8px 14px', borderRadius: '10px',
                background: 'rgba(129,140,248,0.1)', border: '1px solid rgba(129,140,248,0.25)',
                color: 'white', cursor: 'pointer', transition: 'all 0.2s',
              }}
            >
              <span style={{ fontSize: '15px', fontWeight: 800 }}>{asset.symbol}</span>
              <ChevronDown size={14} style={{ color: '#818cf8', transform: assetOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} />
            </button>
            {assetOpen && (
              <div style={{
                position: 'absolute', top: 'calc(100% + 8px)', left: 0, zIndex: 100,
                background: '#131b2f', border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: '14px', overflow: 'hidden', minWidth: '200px',
                boxShadow: '0 16px 48px rgba(0,0,0,0.5)',
              }}>
                {ASSETS.map((a) => (
                  <button
                    key={a.symbol}
                    onClick={() => switchAsset(a)}
                    style={{
                      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                      width: '100%', padding: '11px 16px', background: a.symbol === asset.symbol ? 'rgba(129,140,248,0.08)' : 'none',
                      border: 'none', cursor: 'pointer', color: 'white', fontSize: '13px', fontWeight: 600,
                      transition: 'background 0.15s',
                    }}
                    onMouseEnter={(e) => { if (a.symbol !== asset.symbol) e.currentTarget.style.background = 'rgba(255,255,255,0.04)' }}
                    onMouseLeave={(e) => { if (a.symbol !== asset.symbol) e.currentTarget.style.background = 'none' }}
                  >
                    <span>{a.symbol}</span>
                    <span style={{ fontSize: '12px', color: a.change >= 0 ? '#10b981' : '#f43f5e', fontWeight: 700 }}>
                      {a.change >= 0 ? '+' : ''}{a.change}%
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Divider */}
          <div style={{ width: '1px', height: '32px', background: 'rgba(255,255,255,0.06)', flexShrink: 0 }} />

          {/* Price + change */}
          <div>
            <p style={{ fontSize: '22px', fontWeight: 800, color, lineHeight: 1, fontVariantNumeric: 'tabular-nums' }}>
              ${livePrice.toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </p>
            <p style={{ fontSize: '11px', marginTop: '2px', color, fontWeight: 700, display: 'flex', alignItems: 'center', gap: '3px' }}>
              {isUp ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
              {asset.change >= 0 ? '+' : ''}{asset.change}% (24h)
            </p>
          </div>

          <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
            {[
              { label: '24h High', value: `$${asset.high.toLocaleString()}`, color: '#10b981' },
              { label: '24h Low',  value: `$${asset.low.toLocaleString()}`,  color: '#f43f5e' },
              { label: '24h Volume', value: asset.volume, color: '#94a3b8' },
            ].map(({ label, value, color: c }) => (
              <div key={label}>
                <p style={{ fontSize: '9px', fontWeight: 700, color: '#334155', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '2px' }}>{label}</p>
                <p style={{ fontSize: '13px', fontWeight: 700, color: c, fontVariantNumeric: 'tabular-nums' }}>{value}</p>
              </div>
            ))}
          </div>

          {/* Timeframes */}
          <div style={{ marginLeft: 'auto', display: 'flex', gap: '4px', background: 'rgba(0,0,0,0.25)', borderRadius: '9px', padding: '4px' }}>
            {['1M','5M','15M','1H','4H','1D'].map((t) => (
              <button
                key={t}
                onClick={() => setTf(t)}
                style={{
                  padding: '5px 10px', borderRadius: '7px', fontSize: '11px', fontWeight: 700,
                  background: tf === t ? 'rgba(129,140,248,0.18)' : 'none',
                  border: tf === t ? '1px solid rgba(129,140,248,0.3)' : '1px solid transparent',
                  color: tf === t ? '#a5b4fc' : '#475569', cursor: 'pointer', transition: 'all 0.15s',
                }}
              >{t}</button>
            ))}
          </div>
        </div>
      </Panel>

      {/* ── Main 3-column grid ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 260px 280px', gap: '16px', marginBottom: '16px' }} className="lt-main-grid">

        {/* ── Chart ── */}
        <Panel>
          <PanelHeader>
            <BarChart2 size={15} style={{ color: '#818cf8' }} />
            <span style={{ fontSize: '13px', fontWeight: 700, color: 'white' }}>{asset.symbol} · {tf}</span>
            <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '11px', color: '#10b981', background: 'rgba(16,185,129,0.1)', padding: '2px 8px', borderRadius: '5px', fontWeight: 700 }}>
                Live
              </span>
            </div>
          </PanelHeader>
          <div style={{ padding: '4px 4px 8px' }}>
            <Sparkline data={chartData} color={isUp ? '#10b981' : '#f43f5e'} height={280} fullWidth />
          </div>
          {/* Chart footer stats */}
          <div style={{ display: 'flex', gap: '0', borderTop: '1px solid rgba(255,255,255,0.04)' }}>
            {[
              { label: 'Open',  value: `$${(asset.low + (asset.high - asset.low) * 0.4).toFixed(2)}` },
              { label: 'High',  value: `$${asset.high}` },
              { label: 'Low',   value: `$${asset.low}` },
              { label: 'Close', value: `$${livePrice.toLocaleString()}` },
            ].map(({ label, value }, i, arr) => (
              <div key={label} style={{
                flex: 1, padding: '10px 14px', textAlign: 'center',
                borderRight: i < arr.length - 1 ? '1px solid rgba(255,255,255,0.04)' : 'none',
              }}>
                <p style={{ fontSize: '9px', fontWeight: 700, color: '#334155', textTransform: 'uppercase', letterSpacing: '0.08em' }}>{label}</p>
                <p style={{ fontSize: '12px', fontWeight: 700, color: '#94a3b8', marginTop: '3px' }}>{value}</p>
              </div>
            ))}
          </div>
        </Panel>

        {/* ── Order book ── */}
        <Panel>
          <PanelHeader style={{ padding: '12px 14px' }}>
            <div style={{ display: 'flex', gap: '2px', background: 'rgba(0,0,0,0.2)', borderRadius: '7px', padding: '3px' }}>
              {[{ id: 'book', label: 'Book', icon: List }, { id: 'trades', label: 'Trades', icon: Clock }].map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => setBookTab(id)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '5px',
                    padding: '5px 10px', borderRadius: '5px', fontSize: '11px', fontWeight: 700,
                    background: bookTab === id ? 'rgba(129,140,248,0.15)' : 'none',
                    border: bookTab === id ? '1px solid rgba(129,140,248,0.25)' : '1px solid transparent',
                    color: bookTab === id ? '#a5b4fc' : '#475569', cursor: 'pointer', transition: 'all 0.15s',
                  }}
                >
                  <Icon size={11} />{label}
                </button>
              ))}
            </div>
          </PanelHeader>

          {bookTab === 'book' ? (
            <div style={{ fontSize: '11px', fontVariantNumeric: 'tabular-nums' }}>
              {/* Ask header */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', padding: '6px 12px 4px', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                {['Price (USDT)', 'Size', 'Total'].map((h, i) => (
                  <span key={h} style={{ fontSize: '9px', fontWeight: 700, color: '#334155', textTransform: 'uppercase', letterSpacing: '0.07em', textAlign: i > 0 ? 'right' : 'left' }}>{h}</span>
                ))}
              </div>
              {/* Asks */}
              <div style={{ maxHeight: '155px', overflowY: 'hidden' }}>
                {asks.slice(0, 10).map((a, i) => (
                  <div key={i} style={{ position: 'relative', display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', padding: '3.5px 12px', transition: 'background 0.15s' }}
                    onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.03)'}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'none'}>
                    <DepthBar value={a.size} max={maxAsk} side="ask" />
                    <span style={{ color: '#f43f5e', fontWeight: 600, position: 'relative' }}>{a.price.toLocaleString()}</span>
                    <span style={{ textAlign: 'right', color: '#94a3b8', position: 'relative' }}>{a.size}</span>
                    <span style={{ textAlign: 'right', color: '#64748b', position: 'relative' }}>{a.total.toLocaleString()}</span>
                  </div>
                ))}
              </div>
              {/* Mid price */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', padding: '8px 12px', background: isUp ? 'rgba(16,185,129,0.06)' : 'rgba(244,63,94,0.06)', borderTop: '1px solid rgba(255,255,255,0.04)', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                <span style={{ fontSize: '14px', fontWeight: 800, color, fontVariantNumeric: 'tabular-nums' }}>
                  ${livePrice.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </span>
                {isUp ? <ArrowUpRight size={14} style={{ color }} /> : <ArrowDownRight size={14} style={{ color }} />}
              </div>
              {/* Bids */}
              <div style={{ maxHeight: '155px', overflowY: 'hidden' }}>
                {bids.slice(0, 10).map((b, i) => (
                  <div key={i} style={{ position: 'relative', display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', padding: '3.5px 12px', transition: 'background 0.15s' }}
                    onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.03)'}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'none'}>
                    <DepthBar value={b.size} max={maxBid} side="bid" />
                    <span style={{ color: '#10b981', fontWeight: 600, position: 'relative' }}>{b.price.toLocaleString()}</span>
                    <span style={{ textAlign: 'right', color: '#94a3b8', position: 'relative' }}>{b.size}</span>
                    <span style={{ textAlign: 'right', color: '#64748b', position: 'relative' }}>{b.total.toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            /* Recent Trades tab */
            <div style={{ fontSize: '11px', fontVariantNumeric: 'tabular-nums' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', padding: '6px 12px 4px', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                {['Price', 'Size', 'Time'].map((h, i) => (
                  <span key={h} style={{ fontSize: '9px', fontWeight: 700, color: '#334155', textTransform: 'uppercase', letterSpacing: '0.07em', textAlign: i > 0 ? 'right' : 'left' }}>{h}</span>
                ))}
              </div>
              <div style={{ maxHeight: '370px', overflowY: 'auto' }}>
                {trades.map((t) => (
                  <div key={t.id} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', padding: '4px 12px', transition: 'background 0.15s' }}
                    onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.02)'}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'none'}>
                    <span style={{ color: t.side === 'BUY' ? '#10b981' : '#f43f5e', fontWeight: 600 }}>{t.price.toLocaleString()}</span>
                    <span style={{ textAlign: 'right', color: '#94a3b8' }}>{t.size}</span>
                    <span style={{ textAlign: 'right', color: '#475569' }}>{t.time}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Panel>

        {/* ── Order form ── */}
        <Panel>
          {/* Wallet summary */}
          <div style={{ padding: '14px 16px', borderBottom: '1px solid rgba(255,255,255,0.05)', display: 'flex', gap: '12px' }}>
            <div style={{ flex: 1 }}>
              <p style={{ fontSize: '9px', fontWeight: 700, color: '#334155', textTransform: 'uppercase', letterSpacing: '0.07em' }}>USDT Balance</p>
              <p style={{ fontSize: '14px', fontWeight: 800, color: 'white', marginTop: '3px' }}>${balance.usdt.toLocaleString()}</p>
            </div>
            <div style={{ flex: 1 }}>
              <p style={{ fontSize: '9px', fontWeight: 700, color: '#334155', textTransform: 'uppercase', letterSpacing: '0.07em' }}>{asset.base} Balance</p>
              <p style={{ fontSize: '14px', fontWeight: 800, color: 'white', marginTop: '3px' }}>
                {(balance[asset.base.toLowerCase()] ?? 0).toFixed(4)}
              </p>
            </div>
          </div>

          <div style={{ padding: '14px 16px' }}>
            {/* Buy / Sell toggle */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', marginBottom: '14px' }}>
              {['buy', 'sell'].map((s) => (
                <button
                  key={s}
                  id={`order-side-${s}`}
                  onClick={() => { setOrderSide(s); setOrderAmount(''); setOrderPct(null) }}
                  style={{
                    padding: '10px', borderRadius: '10px', fontWeight: 800, fontSize: '13px',
                    cursor: 'pointer', transition: 'all 0.2s',
                    background: orderSide === s
                      ? s === 'buy' ? 'linear-gradient(135deg,#10b981,#059669)' : 'linear-gradient(135deg,#f43f5e,#e11d48)'
                      : 'rgba(255,255,255,0.04)',
                    border: orderSide === s ? 'none' : '1px solid rgba(255,255,255,0.08)',
                    color: orderSide === s ? 'white' : '#64748b',
                    boxShadow: orderSide === s ? (s === 'buy' ? '0 4px 14px rgba(16,185,129,0.35)' : '0 4px 14px rgba(244,63,94,0.35)') : 'none',
                  }}
                >
                  {s === 'buy' ? '▲ BUY' : '▼ SELL'}
                </button>
              ))}
            </div>

            {/* Order type */}
            <div style={{ display: 'flex', gap: '4px', background: 'rgba(0,0,0,0.2)', borderRadius: '8px', padding: '3px', marginBottom: '14px' }}>
              {['market', 'limit', 'stop'].map((t) => (
                <button
                  key={t}
                  id={`order-type-${t}`}
                  onClick={() => setOrderType(t)}
                  style={{
                    flex: 1, padding: '6px 4px', borderRadius: '6px', fontSize: '11px', fontWeight: 700,
                    background: orderType === t ? 'rgba(129,140,248,0.15)' : 'none',
                    border: orderType === t ? '1px solid rgba(129,140,248,0.3)' : '1px solid transparent',
                    color: orderType === t ? '#a5b4fc' : '#475569', cursor: 'pointer', transition: 'all 0.15s',
                    textTransform: 'capitalize',
                  }}
                >{t}</button>
              ))}
            </div>

            {/* Limit / Stop price input */}
            {orderType !== 'market' && (
              <div style={{ marginBottom: '10px' }}>
                <label style={{ fontSize: '10px', fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.07em', display: 'block', marginBottom: '5px' }}>
                  {orderType === 'limit' ? 'Limit Price' : 'Stop Price'} (USDT)
                </label>
                <div style={{ position: 'relative' }}>
                  <input
                    id="limit-price-input"
                    type="number"
                    value={limitPrice}
                    onChange={(e) => setLimitPrice(e.target.value)}
                    placeholder={livePrice.toString()}
                    style={{
                      width: '100%', padding: '9px 12px', borderRadius: '9px',
                      background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
                      color: 'white', fontSize: '13px', fontFamily: 'inherit', outline: 'none',
                    }}
                    onFocus={(e) => e.target.style.borderColor = 'rgba(129,140,248,0.5)'}
                    onBlur={(e) => e.target.style.borderColor = 'rgba(255,255,255,0.08)'}
                  />
                  <span style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', fontSize: '11px', color: '#475569' }}>USDT</span>
                </div>
              </div>
            )}

            {/* Amount */}
            <div style={{ marginBottom: '10px' }}>
              <label style={{ fontSize: '10px', fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.07em', display: 'block', marginBottom: '5px' }}>
                Amount ({asset.base})
              </label>
              <div style={{ position: 'relative' }}>
                <button
                  onClick={() => setOrderAmount((v) => v ? Math.max(0, Number(v) - 0.001).toFixed(4) : '0.001')}
                  style={{ position: 'absolute', left: '8px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: '#475569', cursor: 'pointer', padding: '2px' }}>
                  <Minus size={12} />
                </button>
                <input
                  id="order-amount-input"
                  type="number"
                  value={orderAmount}
                  onChange={(e) => { setOrderAmount(e.target.value); setOrderPct(null) }}
                  placeholder="0.0000"
                  style={{
                    width: '100%', padding: '9px 40px', textAlign: 'center',
                    borderRadius: '9px',
                    background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
                    color: 'white', fontSize: '13px', fontFamily: 'inherit', outline: 'none',
                  }}
                  onFocus={(e) => e.target.style.borderColor = 'rgba(129,140,248,0.5)'}
                  onBlur={(e) => e.target.style.borderColor = 'rgba(255,255,255,0.08)'}
                />
                <button
                  onClick={() => setOrderAmount((v) => (Number(v || 0) + 0.001).toFixed(4))}
                  style={{ position: 'absolute', right: '8px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: '#475569', cursor: 'pointer', padding: '2px' }}>
                  <Plus size={12} />
                </button>
              </div>
            </div>

            {/* PCT buttons */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: '4px', marginBottom: '12px' }}>
              {[25, 50, 75, 100].map((p) => (
                <button
                  key={p}
                  id={`pct-btn-${p}`}
                  onClick={() => applyPct(p)}
                  style={{
                    padding: '5px 0', borderRadius: '7px', fontSize: '10px', fontWeight: 700,
                    background: orderPct === p ? 'rgba(129,140,248,0.15)' : 'rgba(255,255,255,0.04)',
                    border: orderPct === p ? '1px solid rgba(129,140,248,0.3)' : '1px solid rgba(255,255,255,0.06)',
                    color: orderPct === p ? '#a5b4fc' : '#64748b', cursor: 'pointer', transition: 'all 0.15s',
                  }}
                >{p}%</button>
              ))}
            </div>

            {/* Total */}
            {total && (
              <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '8px 12px', borderRadius: '9px',
                background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)',
                marginBottom: '12px',
              }}>
                <span style={{ fontSize: '11px', color: '#475569', fontWeight: 600 }}>Est. Total</span>
                <span style={{ fontSize: '13px', color: 'white', fontWeight: 800, fontVariantNumeric: 'tabular-nums' }}>
                  ${Number(total).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </span>
              </div>
            )}

            {/* Market price note */}
            {orderType === 'market' && (
              <p style={{ fontSize: '10px', color: '#475569', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Activity size={10} /> Executes at market price ~${livePrice.toLocaleString()}
              </p>
            )}

            {/* Place order */}
            <button
              id="place-order-btn"
              onClick={placeOrder}
              disabled={placing}
              style={{
                width: '100%', padding: '13px', borderRadius: '11px', fontWeight: 800, fontSize: '14px',
                background: placing
                  ? 'rgba(255,255,255,0.08)'
                  : orderSide === 'buy'
                    ? 'linear-gradient(135deg,#10b981 0%,#059669 100%)'
                    : 'linear-gradient(135deg,#f43f5e 0%,#e11d48 100%)',
                border: 'none', color: 'white', cursor: placing ? 'not-allowed' : 'pointer',
                transition: 'all 0.2s', letterSpacing: '0.03em',
                boxShadow: placing ? 'none' : orderSide === 'buy' ? '0 4px 18px rgba(16,185,129,0.4)' : '0 4px 18px rgba(244,63,94,0.4)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
              }}
              onMouseEnter={(e) => { if (!placing) e.currentTarget.style.opacity = '0.88' }}
              onMouseLeave={(e) => { e.currentTarget.style.opacity = '1' }}
            >
              {placing
                ? <><RefreshCw size={14} style={{ animation: 'spin-cw 1s linear infinite' }} /> Placing…</>
                : <>{orderSide === 'buy' ? '▲ PLACE BUY' : '▼ PLACE SELL'} {orderType !== 'market' ? orderType.toUpperCase() : ''}</>
              }
            </button>

            {/* Risk warning */}
            <p style={{ fontSize: '9px', color: '#334155', textAlign: 'center', marginTop: '10px', lineHeight: 1.5 }}>
              ⚠ Paper trading mode. No real funds at risk.
            </p>
          </div>
        </Panel>
      </div>

      {/* ── Positions / Orders / History ── */}
      <Panel>
        {/* Tab bar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
          {[
            { id: 'positions', label: `Open Positions (${positions.length})` },
            { id: 'orders',    label: `Open Orders (${openOrders.length})` },
            { id: 'history',   label: 'Trade History' },
          ].map(({ id, label }) => (
            <button
              key={id}
              id={`pos-tab-${id}`}
              onClick={() => setPosTab(id)}
              style={{
                padding: '14px 20px', fontSize: '12px', fontWeight: 700,
                background: 'none', border: 'none',
                borderBottom: posTab === id ? '2px solid #818cf8' : '2px solid transparent',
                color: posTab === id ? 'white' : '#475569',
                cursor: 'pointer', transition: 'all 0.15s', whiteSpace: 'nowrap',
              }}
            >{label}</button>
          ))}
        </div>

        <div style={{ overflowX: 'auto' }}>

          {/* Open Positions */}
          {posTab === 'positions' && (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                  {['Pair', 'Side', 'Size', 'Entry Price', 'Liq. Price', 'Unrealized P&L', 'Actions'].map((h, i) => (
                    <th key={h} style={{
                      padding: '10px 16px', textAlign: i === 6 ? 'right' : 'left',
                      fontSize: '9px', fontWeight: 700, color: '#334155',
                      textTransform: 'uppercase', letterSpacing: '0.08em',
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {positions.length === 0 && (
                  <tr><td colSpan={7} style={{ padding: '28px', textAlign: 'center', color: '#334155', fontSize: '13px' }}>
                    No open positions
                  </td></tr>
                )}
                {positions.map((pos) => (
                  <tr key={pos.id}
                    style={{ borderBottom: '1px solid rgba(255,255,255,0.03)', transition: 'background 0.15s' }}
                    onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.02)'}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'none'}>
                    <td style={{ padding: '13px 16px', fontWeight: 700, color: 'white' }}>{pos.pair}</td>
                    <td style={{ padding: '13px 16px' }}>
                      <span style={{
                        padding: '3px 9px', borderRadius: '6px', fontSize: '10px', fontWeight: 800, letterSpacing: '0.05em',
                        background: pos.side === 'LONG' ? 'rgba(16,185,129,0.1)' : 'rgba(244,63,94,0.1)',
                        color: pos.side === 'LONG' ? '#10b981' : '#f43f5e',
                        border: `1px solid ${pos.side === 'LONG' ? 'rgba(16,185,129,0.2)' : 'rgba(244,63,94,0.2)'}`,
                      }}>{pos.side}</span>
                    </td>
                    <td style={{ padding: '13px 16px', color: '#94a3b8' }}>{pos.size}</td>
                    <td style={{ padding: '13px 16px', color: '#94a3b8' }}>${pos.entry.toLocaleString()}</td>
                    <td style={{ padding: '13px 16px', color: '#f43f5e' }}>${pos.liq.toLocaleString()}</td>
                    <td style={{ padding: '13px 16px', fontWeight: 700, color: pos.isWin ? '#10b981' : '#f43f5e' }}>
                      <span>{pos.pnl}</span>
                      <span style={{ fontSize: '10px', marginLeft: '6px', opacity: 0.8 }}>{pos.pnlPct}</span>
                    </td>
                    <td style={{ padding: '13px 16px', textAlign: 'right' }}>
                      <button
                        onClick={() => closePosition(pos.id)}
                        style={{
                          padding: '5px 14px', borderRadius: '7px', fontSize: '11px', fontWeight: 700,
                          background: 'rgba(244,63,94,0.08)', border: '1px solid rgba(244,63,94,0.2)',
                          color: '#f43f5e', cursor: 'pointer', transition: 'all 0.15s',
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(244,63,94,0.18)'}
                        onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(244,63,94,0.08)'}
                      >Close</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {/* Open Orders */}
          {posTab === 'orders' && (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                  {['Pair', 'Type', 'Side', 'Price', 'Size', 'Status', 'Actions'].map((h, i) => (
                    <th key={h} style={{
                      padding: '10px 16px', textAlign: i === 6 ? 'right' : 'left',
                      fontSize: '9px', fontWeight: 700, color: '#334155',
                      textTransform: 'uppercase', letterSpacing: '0.08em',
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {openOrders.length === 0 && (
                  <tr><td colSpan={7} style={{ padding: '28px', textAlign: 'center', color: '#334155', fontSize: '13px' }}>
                    No open orders
                  </td></tr>
                )}
                {openOrders.map((o) => (
                  <tr key={o.id}
                    style={{ borderBottom: '1px solid rgba(255,255,255,0.03)', transition: 'background 0.15s' }}
                    onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.02)'}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'none'}>
                    <td style={{ padding: '13px 16px', fontWeight: 700, color: 'white' }}>{o.pair}</td>
                    <td style={{ padding: '13px 16px', color: '#94a3b8' }}>{o.type}</td>
                    <td style={{ padding: '13px 16px' }}>
                      <span style={{
                        padding: '3px 9px', borderRadius: '6px', fontSize: '10px', fontWeight: 800,
                        background: o.side === 'BUY' ? 'rgba(16,185,129,0.1)' : 'rgba(244,63,94,0.1)',
                        color: o.side === 'BUY' ? '#10b981' : '#f43f5e',
                        border: `1px solid ${o.side === 'BUY' ? 'rgba(16,185,129,0.2)' : 'rgba(244,63,94,0.2)'}`,
                      }}>{o.side}</span>
                    </td>
                    <td style={{ padding: '13px 16px', color: '#94a3b8' }}>${o.price.toLocaleString()}</td>
                    <td style={{ padding: '13px 16px', color: '#94a3b8' }}>{o.size}</td>
                    <td style={{ padding: '13px 16px' }}>
                      <span style={{ fontSize: '10px', fontWeight: 700, color: '#f59e0b', background: 'rgba(245,158,11,0.1)', padding: '2px 8px', borderRadius: '5px' }}>
                        {o.status}
                      </span>
                    </td>
                    <td style={{ padding: '13px 16px', textAlign: 'right' }}>
                      <button
                        onClick={() => cancelOrder(o.id)}
                        style={{
                          padding: '5px 14px', borderRadius: '7px', fontSize: '11px', fontWeight: 700,
                          background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
                          color: '#94a3b8', cursor: 'pointer', transition: 'all 0.15s',
                          display: 'inline-flex', alignItems: 'center', gap: '4px',
                        }}
                        onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(244,63,94,0.08)'; e.currentTarget.style.color = '#f43f5e' }}
                        onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; e.currentTarget.style.color = '#94a3b8' }}
                      ><X size={11} /> Cancel</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {/* Trade History */}
          {posTab === 'history' && (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                  {['Pair', 'Side', 'Type', 'Price', 'Size', 'P&L', 'Time'].map((h, i) => (
                    <th key={h} style={{
                      padding: '10px 16px', textAlign: i > 4 ? 'right' : 'left',
                      fontSize: '9px', fontWeight: 700, color: '#334155',
                      textTransform: 'uppercase', letterSpacing: '0.08em',
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[
                  { pair:'BTC/USDT', side:'BUY',  type:'MARKET', price:62100, size:0.05, pnl:'+$71.50', isWin:true,  time:'2 hrs ago' },
                  { pair:'ETH/USDT', side:'SELL', type:'LIMIT',  price:3500,  size:0.8,  pnl:'-$40.00', isWin:false, time:'5 hrs ago' },
                  { pair:'SOL/USDT', side:'BUY',  type:'MARKET', price:140.5, size:2.0,  pnl:'+$9.40',  isWin:true,  time:'1 day ago' },
                  { pair:'BNB/USDT', side:'SELL', type:'LIMIT',  price:592,   size:0.3,  pnl:'+$3.60',  isWin:true,  time:'2 days ago'},
                ].map((t, i) => (
                  <tr key={i}
                    style={{ borderBottom: '1px solid rgba(255,255,255,0.03)', transition: 'background 0.15s' }}
                    onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.02)'}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'none'}>
                    <td style={{ padding: '13px 16px', fontWeight: 700, color: 'white' }}>{t.pair}</td>
                    <td style={{ padding: '13px 16px' }}>
                      <span style={{
                        padding: '3px 9px', borderRadius: '6px', fontSize: '10px', fontWeight: 800,
                        background: t.side === 'BUY' ? 'rgba(16,185,129,0.1)' : 'rgba(244,63,94,0.1)',
                        color: t.side === 'BUY' ? '#10b981' : '#f43f5e',
                        border: `1px solid ${t.side === 'BUY' ? 'rgba(16,185,129,0.2)' : 'rgba(244,63,94,0.2)'}`,
                      }}>{t.side}</span>
                    </td>
                    <td style={{ padding: '13px 16px', color: '#64748b' }}>{t.type}</td>
                    <td style={{ padding: '13px 16px', color: '#94a3b8' }}>${t.price.toLocaleString()}</td>
                    <td style={{ padding: '13px 16px', color: '#94a3b8' }}>{t.size}</td>
                    <td style={{ padding: '13px 16px', textAlign: 'right', fontWeight: 700, color: t.isWin ? '#10b981' : '#f43f5e' }}>{t.pnl}</td>
                    <td style={{ padding: '13px 16px', textAlign: 'right', color: '#475569' }}>{t.time}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </Panel>

      {/* ── Responsive styles ── */}
      <style>{`
        @media (max-width: 1100px) {
          .lt-main-grid { grid-template-columns: 1fr 240px !important; }
          .lt-main-grid > *:last-child { grid-column: 1 / -1; }
        }
        @media (max-width: 720px) {
          .lt-main-grid { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </div>
  )
}
