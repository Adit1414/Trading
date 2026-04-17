import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { RefreshCw, ChevronDown, Wifi, WifiOff } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { supabase } from '../lib/supabaseClient'
import {
  approveOrder,
  createPrivateWs,
  createPublicWs,
  fetchOhlcv,
  getOpenOrders,
  getPositions,
  getTradeHistory,
  getWalletBalances,
  panicCancelOrder,
  panicClosePosition,
} from '../api/live'
import LiveChart from '../components/LiveChart'

// ── Constants ────────────────────────────────────────────────────────────────

const SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT']

function toWsBase() {
  const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
  const wsBase = apiBase.replace(/^http/, 'ws')
  return wsBase.endsWith('/api/v1') ? wsBase : `${wsBase}/api/v1`
}

function normalizePair(symbol) {
  if (typeof symbol !== 'string' || !symbol) return ''
  if (symbol.includes('/')) return symbol
  if (symbol.endsWith('USDT')) return `${symbol.slice(0, -4)}/USDT`
  return symbol
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function LiveTradingPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [symbol, setSymbol] = useState('BTCUSDT')
  const [symbolMenuOpen, setSymbolMenuOpen] = useState(false)

  const [ticker, setTicker] = useState(null)
  const [orderBook, setOrderBook] = useState({ asks: [], bids: [] })
  const [ohlcvData, setOhlcvData] = useState([])   // fed into <LiveChart>

  const [balances, setBalances] = useState({ live: {}, paper: {} })
  const [positions, setPositions] = useState([])
  const [orders, setOrders] = useState([])
  const [history, setHistory] = useState([])
  const [activeTab, setActiveTab] = useState('positions')

  const [approvalRequest, setApprovalRequest] = useState(null)
  const [approvingId, setApprovingId] = useState(null)
  const [closingId, setClosingId] = useState(null)
  const [cancellingId, setCancellingId] = useState(null)
  const [refreshing, setRefreshing] = useState(false)
  const [wsConnected, setWsConnected] = useState(false)

  // Refs
  const mountedRef = useRef(true)           // lifecycle guard for WS callbacks
  const publicWsRef = useRef(null)          // handle from createPublicWs
  const privateWsRef = useRef(null)         // handle from createPrivateWs
  const chartRef = useRef(null)             // LiveChart imperative ref

  // ── REST data loader (also used as onReconnect callback) ─────────────────

  const loadRestData = useCallback(async () => {
    setRefreshing(true)
    try {
      const [wallet, pos, openOrders, trades] = await Promise.all([
        getWalletBalances(),
        getPositions(),
        getOpenOrders(),
        getTradeHistory(1, 50),
      ])
      if (!mountedRef.current) return
      setBalances(wallet || { live: {}, paper: {} })
      setPositions(Array.isArray(pos) ? pos : [])
      setOrders(Array.isArray(openOrders) ? openOrders : [])
      setHistory(Array.isArray(trades) ? trades : [])
    } catch (err) {
      console.error('Failed loading live trading data:', err)
    } finally {
      if (mountedRef.current) setRefreshing(false)
    }
  }, [])

  // ── Initial REST load ─────────────────────────────────────────────────────

  useEffect(() => {
    loadRestData()
  }, [loadRestData])

  // ── OHLCV fetch (triggered by mount + symbol change) ─────────────────────

  const loadOhlcv = useCallback(async (sym) => {
    try {
      const data = await fetchOhlcv(sym, '1m', 100)
      if (!mountedRef.current) return
      setOhlcvData(data)
    } catch (err) {
      console.error('[Chart] Failed to fetch OHLCV:', err)
    }
  }, [])

  useEffect(() => {
    loadOhlcv(symbol)
  }, [symbol, loadOhlcv])

  // ── WebSocket setup (torn down and rebuilt on symbol change) ──────────────

  useEffect(() => {
    mountedRef.current = true
    const wsBase = toWsBase()

    // ── Public WS message handler ─────────────────────────────────────────

    const publicHandlers = {
      onmessage(event) {
        if (!mountedRef.current) return
        try {
          const data = JSON.parse(event.data)
          const type = data?.type
          const payload = data?.payload

          if (type === 'ticker' && Array.isArray(payload)) {
            const match = payload.find((i) => (i?.s || i?.symbol) === symbol) || 
                          payload.find((i) => (i?.s || i?.symbol) === 'BTCUSDT') || 
                          payload[0]
            if (match) setTicker(match)
            return
          }

          if ((type === 'book_depth' || type === 'depth') && payload) {
            setOrderBook({
              asks: Array.isArray(payload.asks) ? payload.asks.slice(0, 15) : [],
              bids: Array.isArray(payload.bids) ? payload.bids.slice(0, 15) : [],
            })
            return
          }

          if (type?.startsWith('kline') || type === 'kline') {
            const k = payload?.k || payload
            if (!k) return
            const time = Math.floor((k.t || k.T || Date.now()) / 1000)
            const ohlc = {
              time,
              open:  parseFloat(k.o),
              high:  parseFloat(k.h),
              low:   parseFloat(k.l),
              close: parseFloat(k.c),
            }
            if ([ohlc.open, ohlc.high, ohlc.low, ohlc.close].some((v) => !Number.isFinite(v))) return
            chartRef.current?.updateCandle(ohlc)
          }
        } catch (e) {
          console.error('[LiveWS] Public stream parse error:', e)
        }
      },
      onerror(err) {
        console.error('[LiveWS] Public stream error:', err)
      }
    }

    publicWsRef.current = createPublicWs(wsBase, publicHandlers, () => {
      setWsConnected(true)
      toast('Market stream reconnected — re-syncing data.', { icon: '🔄' })
      loadRestData()
    }, mountedRef)

    setWsConnected(true)

    // ── Private WS ────────────────────────────────────────────────────────

    supabase.auth.getSession().then(({ data }) => {
      const token = data?.session?.access_token
      if (!token || !mountedRef.current) return

      const privateHandlers = {
        async onmessage(event) {
          if (!mountedRef.current) return
          try {
            const msg = JSON.parse(event.data)
            const type = msg?.type
            const payload = msg?.payload || {}

            if (type === 'BALANCE_UPDATED') {
              setBalances((prev) => ({ ...prev, ...payload }))
            }
            if (type === 'POSITION_UPDATED' || type === 'ORDER_EXECUTED' || type === 'ORDER_APPROVED') {
              await loadRestData()
            }
            if (type === 'ORDER_APPROVAL_REQUIRED' || type === 'APPROVAL_REQUESTED') {
              const approval = {
                id: payload.order_id || payload.id,
                botName: payload.bot_name || payload.botName || 'Bot',
                pair: normalizePair(payload.symbol || payload.pair || ''),
                side: (payload.side || '').toUpperCase(),
                size: payload.quantity || payload.size,
              }
              setApprovalRequest(approval)
              toast(
                `Approval requested: ${approval.botName} ${approval.side} ${approval.pair} ${approval.size ?? ''}`,
                { icon: '⚠️' }
              )
            }
          } catch (e) {
            console.error('[LiveWS] Private stream parse error:', e)
          }
        },
        onerror(err) {
          console.error('[LiveWS] Private stream error:', err)
        }
      }

      privateWsRef.current = createPrivateWs(wsBase, token, privateHandlers, loadRestData, mountedRef)
    })

    return () => {
      mountedRef.current = false
      setWsConnected(false)
      publicWsRef.current?.close()
      privateWsRef.current?.close()
      publicWsRef.current = null
      privateWsRef.current = null
    }
  }, [symbol, loadRestData])   // re-runs on symbol change → tears down + rebuilds WS

  // ── Symbol change handler ─────────────────────────────────────────────────

  const handleSymbolChange = (newSymbol) => {
    if (newSymbol === symbol) return
    setSymbolMenuOpen(false)
    // Clear market data for previous symbol
    setOrderBook({ asks: [], bids: [] })
    setOhlcvData([])
    setTicker(null)
    // Setting `symbol` triggers the WS useEffect to tear down and rebuild
    setSymbol(newSymbol)
  }

  // ── Action handlers ───────────────────────────────────────────────────────

  const handleApprove = useCallback(async (orderId) => {
    if (!orderId) { toast.error('Missing order id.'); return }
    setApprovingId(orderId)
    try {
      await approveOrder(orderId)
      toast.success('Order approved successfully.')
      setApprovalRequest(null)
      await loadRestData()
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Failed to approve order.')
    } finally {
      setApprovingId(null)
    }
  }, [loadRestData])

  useEffect(() => {
    const orderIdToApprove = searchParams.get("approve_order");
    if (orderIdToApprove) {
      // Immediately clear the URL parameter so it doesn't trigger again on reload
      setSearchParams({}); 
      // Trigger the approval process
      handleApprove(orderIdToApprove);
    }
  }, [searchParams, setSearchParams, handleApprove]);

  const handleClosePosition = async (positionId) => {
    setClosingId(positionId)
    try {
      await panicClosePosition(positionId)
      toast.success('Position closed.')
      await loadRestData()
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Failed to close position.')
    } finally {
      setClosingId(null)
    }
  }

  const handleCancelOrder = async (orderId) => {
    setCancellingId(orderId)
    try {
      await panicCancelOrder(orderId)
      toast.success('Order cancelled.')
      await loadRestData()
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Failed to cancel order.')
    } finally {
      setCancellingId(null)
    }
  }

  // ── Memos ─────────────────────────────────────────────────────────────────

  const liveUsdt    = useMemo(() => balances?.live?.USDT ?? 0, [balances])
  const paperEquity = useMemo(() => balances?.paper?.total_equity ?? 0, [balances])
  const currentPrice = useMemo(() => Number(ticker?.c || ticker?.lastPrice || 0), [ticker])
  const priceChange  = useMemo(() => Number(ticker?.P || ticker?.priceChangePercent || 0), [ticker])

  // ── Styles (shared tokens) ────────────────────────────────────────────────

  const card = {
    background: 'linear-gradient(145deg, #131b2f 0%, #0f1729 100%)',
    border: '1px solid rgba(255,255,255,0.06)',
    borderRadius: '20px',
    padding: '20px',
    boxShadow: '0 4px 24px rgba(0,0,0,0.3)',
  }

  // ── Render ────────────────────────────────────────────────────────────────

  if (!symbol) return <div style={{ color: 'white', padding: '40px' }}>Loading...</div>

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '28px 24px', minHeight: '100vh' }}>

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h1 style={{ color: 'white', fontSize: '24px', fontWeight: 700, letterSpacing: '-0.02em' }}>Live Trading</h1>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
            {wsConnected
              ? <><Wifi size={12} style={{ color: '#10b981' }} /><span style={{ fontSize: '12px', color: '#10b981' }}>Live</span></>
              : <><WifiOff size={12} style={{ color: '#f43f5e' }} /><span style={{ fontSize: '12px', color: '#f43f5e' }}>Reconnecting…</span></>
            }
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>

          {/* Symbol selector */}
          <div style={{ position: 'relative' }}>
            <button
              id="symbol-selector-btn"
              onClick={() => setSymbolMenuOpen((o) => !o)}
              style={{
                display: 'flex', alignItems: 'center', gap: '6px',
                padding: '9px 14px', borderRadius: '12px',
                border: '1px solid rgba(129,140,248,0.3)',
                background: 'rgba(129,140,248,0.1)', color: '#a5b4fc',
                fontSize: '13px', fontWeight: 700, cursor: 'pointer',
              }}
            >
              {symbol} <ChevronDown size={14} />
            </button>
            {symbolMenuOpen && (
              <div style={{
                position: 'absolute', top: '42px', right: 0, zIndex: 50,
                background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '12px', overflow: 'hidden', minWidth: '130px',
                boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
              }}>
                {SYMBOLS.map((sym) => (
                  <button
                    key={sym}
                    id={`symbol-option-${sym.toLowerCase()}`}
                    onClick={() => handleSymbolChange(sym)}
                    style={{
                      width: '100%', padding: '10px 16px', textAlign: 'left',
                      background: sym === symbol ? 'rgba(129,140,248,0.15)' : 'transparent',
                      color: sym === symbol ? '#a5b4fc' : '#94a3b8',
                      fontSize: '13px', fontWeight: sym === symbol ? 700 : 500,
                      border: 'none', cursor: 'pointer',
                    }}
                    onMouseEnter={(e) => { if (sym !== symbol) e.currentTarget.style.background = 'rgba(255,255,255,0.05)' }}
                    onMouseLeave={(e) => { if (sym !== symbol) e.currentTarget.style.background = 'transparent' }}
                  >
                    {normalizePair(sym)}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Refresh */}
          <button
            id="live-refresh-btn"
            onClick={loadRestData}
            disabled={refreshing}
            style={{
              display: 'flex', alignItems: 'center', gap: '6px',
              padding: '9px 14px', borderRadius: '12px',
              border: '1px solid rgba(255,255,255,0.1)',
              background: 'transparent', color: '#94a3b8',
              fontSize: '13px', fontWeight: 600, cursor: 'pointer',
            }}
          >
            <RefreshCw size={13} style={{ animation: refreshing ? 'spin-cw 0.8s linear infinite' : 'none' }} />
            Refresh
          </button>
        </div>
      </div>

      {/* ── Approval banner ────────────────────────────────────────────────── */}
      {approvalRequest && (
        <div style={{
          marginBottom: '20px', padding: '16px 20px', borderRadius: '16px',
          border: '1px solid rgba(245,158,11,0.4)',
          background: 'linear-gradient(145deg, rgba(245,158,11,0.08) 0%, rgba(245,158,11,0.04) 100%)',
        }}>
          <p style={{ color: '#f59e0b', fontWeight: 700, marginBottom: '6px', fontSize: '13px', letterSpacing: '0.08em', textTransform: 'uppercase' }}>⚠ Approval Required</p>
          <p style={{ color: 'white', fontSize: '14px' }}>
            <strong>{approvalRequest.botName}</strong> wants to place{' '}
            <strong style={{ color: approvalRequest.side === 'BUY' ? '#10b981' : '#f43f5e' }}>{approvalRequest.side}</strong>{' '}
            on <strong>{approvalRequest.pair}</strong> for{' '}
            <strong>{approvalRequest.size}</strong>.
          </p>
          <button
            id="approve-order-btn"
            onClick={() => handleApprove(approvalRequest.id)}
            disabled={approvingId === approvalRequest.id}
            style={{
              marginTop: '12px', padding: '8px 18px', borderRadius: '10px',
              border: 'none', color: 'white',
              background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
              fontWeight: 700, fontSize: '13px', cursor: 'pointer',
              opacity: approvingId === approvalRequest.id ? 0.6 : 1,
            }}
          >
            {approvingId === approvalRequest.id ? 'Approving…' : 'Approve Order'}
          </button>
        </div>
      )}

      {/* ── KPI Cards ──────────────────────────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', marginBottom: '20px' }}>
        {/* Price */}
        <div style={card}>
          <p style={{ color: '#64748b', fontSize: '11px', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '8px' }}>{normalizePair(symbol)} Price</p>
          <p style={{ color: 'white', fontSize: '22px', fontWeight: 700, lineHeight: 1 }}>
            {currentPrice ? `$${currentPrice.toLocaleString(undefined, { maximumFractionDigits: 2 })}` : '—'}
          </p>
          {priceChange !== 0 && (
            <p style={{ fontSize: '12px', fontWeight: 700, marginTop: '4px', color: priceChange >= 0 ? '#10b981' : '#f43f5e' }}>
              {priceChange >= 0 ? '+' : ''}{priceChange.toFixed(2)}% 24h
            </p>
          )}
        </div>

        {/* Live USDT */}
        <div style={card}>
          <p style={{ color: '#64748b', fontSize: '11px', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '8px' }}>Live USDT</p>
          <p style={{ color: 'white', fontSize: '22px', fontWeight: 700, lineHeight: 1 }}>${Number(liveUsdt).toLocaleString(undefined, { maximumFractionDigits: 2 })}</p>
        </div>

        {/* Paper Equity */}
        <div style={card}>
          <p style={{ color: '#64748b', fontSize: '11px', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '8px' }}>Paper Equity</p>
          <p style={{ color: 'white', fontSize: '22px', fontWeight: 700, lineHeight: 1 }}>${Number(paperEquity).toLocaleString(undefined, { maximumFractionDigits: 2 })}</p>
        </div>
      </div>

      {/* ── Chart + Order Book ─────────────────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '16px', marginBottom: '20px' }} className="live-chart-row">

        {/* Candlestick chart */}
        <div style={{ ...card, padding: '16px' }}>
          <LiveChart ref={chartRef} initialData={ohlcvData} symbol={normalizePair(symbol)} />
        </div>

        {/* Order Book */}
        <div style={{ ...card }}>
          <p style={{ color: 'white', fontWeight: 700, fontSize: '14px', marginBottom: '14px' }}>Order Book</p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <p style={{ color: '#10b981', fontWeight: 700, fontSize: '11px', letterSpacing: '0.08em', marginBottom: '8px', textTransform: 'uppercase' }}>Bids</p>
              {ticker ? (orderBook.bids || []).slice(0, 10).map((b, idx) => (
                <div key={`b-${idx}`} style={{ display: 'flex', justifyContent: 'space-between', color: '#10b981', fontSize: '12px', padding: '2px 0', opacity: 0.8 }}>
                  <span>{b?.[0] ? Number(b[0]).toFixed(2) : '—'}</span>
                  <span style={{ color: '#cbd5e1' }}>{b?.[1] ? Number(b[1]).toFixed(4) : '—'}</span>
                </div>
              )) : <div style={{ fontSize: '12px', color: '#475569' }}>Loading...</div>}
            </div>
            <div>
              <p style={{ color: '#f43f5e', fontWeight: 700, fontSize: '11px', letterSpacing: '0.08em', marginBottom: '8px', textTransform: 'uppercase' }}>Asks</p>
              {ticker ? (orderBook.asks || []).slice(0, 10).map((a, idx) => (
                <div key={`a-${idx}`} style={{ display: 'flex', justifyContent: 'space-between', color: '#f43f5e', fontSize: '12px', padding: '2px 0', opacity: 0.8 }}>
                  <span>{a?.[0] ? Number(a[0]).toFixed(2) : '—'}</span>
                  <span style={{ color: '#cbd5e1' }}>{a?.[1] ? Number(a[1]).toFixed(4) : '—'}</span>
                </div>
              )) : <div style={{ fontSize: '12px', color: '#475569' }}>Loading...</div>}
            </div>
          </div>
        </div>
      </div>

      {/* ── Tab Navigation ────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
        {['positions', 'orders', 'history'].map((tab) => (
          <button
            key={tab}
            id={`tab-${tab}`}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '8px 16px', borderRadius: '10px',
              border: activeTab === tab ? '1px solid rgba(129,140,248,0.4)' : '1px solid rgba(255,255,255,0.08)',
              background: activeTab === tab ? 'rgba(129,140,248,0.15)' : 'transparent',
              color: activeTab === tab ? '#a5b4fc' : '#64748b',
              fontSize: '12px', fontWeight: 700, letterSpacing: '0.08em',
              textTransform: 'uppercase', cursor: 'pointer', transition: 'all 0.15s',
            }}
          >
            {tab}
            {tab === 'positions' && positions.length > 0 && (
              <span style={{ marginLeft: '6px', background: '#818cf8', color: 'white', borderRadius: '4px', padding: '1px 5px', fontSize: '10px' }}>{positions.length}</span>
            )}
            {tab === 'orders' && orders.length > 0 && (
              <span style={{ marginLeft: '6px', background: '#f59e0b', color: 'white', borderRadius: '4px', padding: '1px 5px', fontSize: '10px' }}>{orders.length}</span>
            )}
          </button>
        ))}
      </div>

      {/* ── Tab Content ───────────────────────────────────────────────────── */}
      <div style={card}>
        {activeTab === 'positions' && (
          positions.length === 0
            ? <p style={{ color: '#475569', textAlign: 'center', padding: '32px 0' }}>No active positions.</p>
            : positions.map((p) => (
                <div key={p.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <div>
                    <span style={{ color: 'white', fontWeight: 700 }}>{normalizePair(p.pair)}</span>
                    <span style={{ marginLeft: '10px', padding: '2px 8px', borderRadius: '6px', fontSize: '11px', fontWeight: 700, background: p.side === 'BUY' ? 'rgba(16,185,129,0.12)' : 'rgba(244,63,94,0.12)', color: p.side === 'BUY' ? '#10b981' : '#f43f5e', border: `1px solid ${p.side === 'BUY' ? 'rgba(16,185,129,0.2)' : 'rgba(244,63,94,0.2)'}` }}>{p.side}</span>
                    <span style={{ marginLeft: '10px', color: '#64748b', fontSize: '13px' }}>{p.size} units</span>
                  </div>
                  <button
                    id={`close-pos-${p.id}`}
                    onClick={() => handleClosePosition(p.id)}
                    disabled={closingId === p.id}
                    style={{ padding: '7px 14px', borderRadius: '8px', border: '1px solid rgba(244,63,94,0.3)', background: 'rgba(244,63,94,0.1)', color: '#f43f5e', fontWeight: 700, fontSize: '12px', cursor: 'pointer' }}
                  >
                    {closingId === p.id ? 'Closing…' : 'Close'}
                  </button>
                </div>
              ))
        )}

        {activeTab === 'orders' && (
          orders.length === 0
            ? <p style={{ color: '#475569', textAlign: 'center', padding: '32px 0' }}>No open orders.</p>
            : orders.map((o) => (
                <div key={o.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <div>
                    <span style={{ color: 'white', fontWeight: 700 }}>{normalizePair(o.symbol)}</span>
                    <span style={{ marginLeft: '10px', padding: '2px 8px', borderRadius: '6px', fontSize: '11px', fontWeight: 700, background: o.side === 'BUY' ? 'rgba(16,185,129,0.12)' : 'rgba(244,63,94,0.12)', color: o.side === 'BUY' ? '#10b981' : '#f43f5e', border: `1px solid ${o.side === 'BUY' ? 'rgba(16,185,129,0.2)' : 'rgba(244,63,94,0.2)'}` }}>{o.side}</span>
                    <span style={{ marginLeft: '10px', color: '#64748b', fontSize: '13px' }}>{o.quantity} · {o.status}</span>
                  </div>
                  <button
                    id={`cancel-order-${o.id}`}
                    onClick={() => handleCancelOrder(o.id)}
                    disabled={cancellingId === o.id}
                    style={{ padding: '7px 14px', borderRadius: '8px', border: '1px solid rgba(71,85,105,0.4)', background: 'rgba(71,85,105,0.15)', color: '#94a3b8', fontWeight: 700, fontSize: '12px', cursor: 'pointer' }}
                  >
                    {cancellingId === o.id ? 'Cancelling…' : 'Cancel'}
                  </button>
                </div>
              ))
        )}

        {activeTab === 'history' && (
          history.length === 0
            ? <p style={{ color: '#475569', textAlign: 'center', padding: '32px 0' }}>No trade history.</p>
            : history.map((h) => (
                <div key={h.id} style={{ padding: '12px 0', borderBottom: '1px solid rgba(255,255,255,0.05)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <span style={{ color: 'white', fontWeight: 700 }}>{normalizePair(h.symbol)}</span>
                    <span style={{ marginLeft: '10px', padding: '2px 8px', borderRadius: '6px', fontSize: '11px', fontWeight: 700, background: h.side === 'BUY' ? 'rgba(16,185,129,0.12)' : 'rgba(244,63,94,0.12)', color: h.side === 'BUY' ? '#10b981' : '#f43f5e', border: `1px solid ${h.side === 'BUY' ? 'rgba(16,185,129,0.2)' : 'rgba(244,63,94,0.2)'}` }}>{h.side}</span>
                    <span style={{ marginLeft: '10px', color: '#64748b', fontSize: '13px' }}>{h.quantity} @ ${Number(h.execution_price).toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
                  </div>
                  <span style={{ color: '#475569', fontSize: '12px' }}>{new Date(h.executed_at).toLocaleString()}</span>
                </div>
              ))
        )}
      </div>

      {/* Responsive styles */}
      <style>{`
        @media (max-width: 900px) {
          .live-chart-row { grid-template-columns: 1fr !important; }
        }
        @keyframes spin-cw {
          from { transform: rotate(0deg); }
          to   { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}
