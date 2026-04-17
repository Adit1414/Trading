import { useEffect, useMemo, useState } from 'react'
import { RefreshCw } from 'lucide-react'
import toast from 'react-hot-toast'
import { supabase } from '../lib/supabaseClient'
import {
  approveOrder,
  getOpenOrders,
  getPositions,
  getTradeHistory,
  getWalletBalances,
  panicCancelOrder,
  panicClosePosition,
} from '../api/live'

function toWsBase() {
  const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
  const wsBase = apiBase.replace(/^http/, 'ws')
  return wsBase.endsWith('/api/v1') ? wsBase : `${wsBase}/api/v1`
}

function normalizePair(symbol) {
  if (!symbol) return ''
  if (symbol.includes('/')) return symbol
  if (symbol.endsWith('USDT')) return `${symbol.slice(0, -4)}/USDT`
  return symbol
}

export default function LiveTradingPage() {
  const [ticker, setTicker] = useState(null)
  const [orderBook, setOrderBook] = useState({ asks: [], bids: [] })
  const [klines, setKlines] = useState([])
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

  const loadRestData = async () => {
    setRefreshing(true)
    try {
      const [wallet, pos, openOrders, trades] = await Promise.all([
        getWalletBalances(),
        getPositions(),
        getOpenOrders(),
        getTradeHistory(1, 50),
      ])
      setBalances(wallet || { live: {}, paper: {} })
      setPositions(Array.isArray(pos) ? pos : [])
      setOrders(Array.isArray(openOrders) ? openOrders : [])
      setHistory(Array.isArray(trades) ? trades : [])
    } catch (err) {
      console.error('Failed loading live trading data:', err)
    } finally {
      setRefreshing(false)
    }
  }

  useEffect(() => {
    loadRestData()
  }, [])

  useEffect(() => {
    let publicWs
    let privateWs
    let mounted = true

    const connect = async () => {
      const wsBase = toWsBase()
      publicWs = new WebSocket(`${wsBase}/ws/market`)

      publicWs.onmessage = (event) => {
        if (!mounted) return
        try {
          const data = JSON.parse(event.data)
          const type = data?.type
          const payload = data?.payload

          if (type === 'ticker' && Array.isArray(payload)) {
            const btc = payload.find((i) => i?.s === 'BTCUSDT') || payload[0]
            if (btc) setTicker(btc)
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
            const close = Number(k.c)
            if (!Number.isFinite(close)) return
            setKlines((prev) => [...prev.slice(-99), { t: k.t || Date.now(), close }])
          }
        } catch (e) {
          console.error('Public WS parse error:', e)
        }
      }

      const { data } = await supabase.auth.getSession()
      const token = data?.session?.access_token
      if (!token) return

      privateWs = new WebSocket(`${wsBase}/ws/private?token=${encodeURIComponent(token)}`)
      privateWs.onmessage = async (event) => {
        if (!mounted) return
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
          console.error('Private WS parse error:', e)
        }
      }
    }

    connect()
    return () => {
      mounted = false
      if (publicWs) publicWs.close()
      if (privateWs) privateWs.close()
    }
  }, [])

  const handleApprove = async (orderId) => {
    if (!orderId) {
      toast.error('Missing order id for approval request.')
      return
    }
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
  }

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

  const liveUsdt = useMemo(() => balances?.live?.USDT ?? 0, [balances])
  const paperEquity = useMemo(() => balances?.paper?.total_equity ?? 0, [balances])
  const currentPrice = useMemo(() => Number(ticker?.c || ticker?.lastPrice || 0), [ticker])

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h1 style={{ color: 'white', fontSize: '24px', fontWeight: 700 }}>Live Trading</h1>
        <button
          onClick={loadRestData}
          disabled={refreshing}
          style={{ padding: '8px 12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.15)', background: 'transparent', color: 'white' }}
        >
          {refreshing ? <RefreshCw size={14} style={{ animation: 'spin-cw 1s linear infinite' }} /> : 'Refresh'}
        </button>
      </div>

      {approvalRequest && (
        <div style={{ marginBottom: '16px', padding: '14px', borderRadius: '10px', border: '1px solid rgba(245,158,11,0.5)', background: 'rgba(245,158,11,0.1)' }}>
          <p style={{ color: '#f59e0b', fontWeight: 700, marginBottom: '8px' }}>Approval Requested</p>
          <p style={{ color: 'white', fontSize: '14px' }}>
            <strong>{approvalRequest.botName}</strong> wants to place <strong>{approvalRequest.side}</strong> on{' '}
            <strong>{approvalRequest.pair}</strong> for <strong>{approvalRequest.size}</strong>.
          </p>
          <button
            onClick={() => handleApprove(approvalRequest.id)}
            disabled={approvingId === approvalRequest.id}
            style={{ marginTop: '10px', padding: '8px 12px', borderRadius: '8px', border: 'none', color: 'white', background: '#10b981', fontWeight: 700 }}
          >
            {approvingId === approvalRequest.id ? 'Approving...' : 'Approve'}
          </button>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px', marginBottom: '16px' }}>
        <div style={{ background: '#111827', padding: '12px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.08)' }}>
          <p style={{ color: '#9ca3af', fontSize: '12px' }}>BTCUSDT Price</p>
          <p style={{ color: 'white', fontSize: '20px', fontWeight: 700 }}>{currentPrice ? `$${currentPrice.toLocaleString()}` : '--'}</p>
        </div>
        <div style={{ background: '#111827', padding: '12px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.08)' }}>
          <p style={{ color: '#9ca3af', fontSize: '12px' }}>Live USDT</p>
          <p style={{ color: 'white', fontSize: '20px', fontWeight: 700 }}>${Number(liveUsdt).toLocaleString()}</p>
        </div>
        <div style={{ background: '#111827', padding: '12px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.08)' }}>
          <p style={{ color: '#9ca3af', fontSize: '12px' }}>Paper Equity</p>
          <p style={{ color: 'white', fontSize: '20px', fontWeight: 700 }}>${Number(paperEquity).toLocaleString()}</p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '12px', marginBottom: '16px' }}>
        <div style={{ background: '#111827', padding: '12px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.08)' }}>
          <p style={{ color: 'white', fontWeight: 700, marginBottom: '8px' }}>Kline Close (last 100)</p>
          <div style={{ maxHeight: '240px', overflow: 'auto', color: '#cbd5e1', fontSize: '12px' }}>
            {klines.length === 0 ? 'Waiting for kline data...' : klines.map((k) => <div key={k.t}>{new Date(k.t).toLocaleTimeString()} - {k.close}</div>)}
          </div>
        </div>
        <div style={{ background: '#111827', padding: '12px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.08)' }}>
          <p style={{ color: 'white', fontWeight: 700, marginBottom: '8px' }}>Order Book</p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
            <div>
              <p style={{ color: '#10b981', fontWeight: 700, marginBottom: '6px' }}>Bids</p>
              {(orderBook.bids || []).slice(0, 10).map((b, idx) => <div key={`b-${idx}`} style={{ color: '#cbd5e1', fontSize: '12px' }}>{b[0]} / {b[1]}</div>)}
            </div>
            <div>
              <p style={{ color: '#f43f5e', fontWeight: 700, marginBottom: '6px' }}>Asks</p>
              {(orderBook.asks || []).slice(0, 10).map((a, idx) => <div key={`a-${idx}`} style={{ color: '#cbd5e1', fontSize: '12px' }}>{a[0]} / {a[1]}</div>)}
            </div>
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
        {['positions', 'orders', 'history'].map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '8px 12px',
              borderRadius: '8px',
              border: activeTab === tab ? '1px solid #818cf8' : '1px solid rgba(255,255,255,0.1)',
              background: activeTab === tab ? 'rgba(129,140,248,0.2)' : 'transparent',
              color: 'white',
            }}
          >
            {tab.toUpperCase()}
          </button>
        ))}
      </div>

      {activeTab === 'positions' && (
        <div style={{ background: '#111827', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.08)', padding: '10px' }}>
          {positions.length === 0 ? <p style={{ color: '#9ca3af' }}>No active positions.</p> : positions.map((p) => (
            <div key={p.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
              <span style={{ color: 'white' }}>{normalizePair(p.pair)} · {p.side} · {p.size}</span>
              <button
                onClick={() => handleClosePosition(p.id)}
                disabled={closingId === p.id}
                style={{ padding: '6px 10px', borderRadius: '6px', border: 'none', background: '#f43f5e', color: 'white' }}
              >
                {closingId === p.id ? 'Closing...' : 'Close'}
              </button>
            </div>
          ))}
        </div>
      )}

      {activeTab === 'orders' && (
        <div style={{ background: '#111827', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.08)', padding: '10px' }}>
          {orders.length === 0 ? <p style={{ color: '#9ca3af' }}>No open orders.</p> : orders.map((o) => (
            <div key={o.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
              <span style={{ color: 'white' }}>{normalizePair(o.symbol)} · {o.side} · {o.quantity} · {o.status}</span>
              <button
                onClick={() => handleCancelOrder(o.id)}
                disabled={cancellingId === o.id}
                style={{ padding: '6px 10px', borderRadius: '6px', border: 'none', background: '#475569', color: 'white' }}
              >
                {cancellingId === o.id ? 'Cancelling...' : 'Cancel'}
              </button>
            </div>
          ))}
        </div>
      )}

      {activeTab === 'history' && (
        <div style={{ background: '#111827', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.08)', padding: '10px' }}>
          {history.length === 0 ? <p style={{ color: '#9ca3af' }}>No trade history.</p> : history.map((h) => (
            <div key={h.id} style={{ padding: '8px 0', borderBottom: '1px solid rgba(255,255,255,0.05)', color: 'white' }}>
              {normalizePair(h.symbol)} · {h.side} · {h.quantity} @ {h.execution_price} · {new Date(h.executed_at).toLocaleString()}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
