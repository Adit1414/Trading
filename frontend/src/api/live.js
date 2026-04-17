/**
 * frontend/src/api/live.js
 * ─────────────────────────
 * REST helpers + resilient WebSocket factories for the Live Trading page.
 *
 * WebSocket design
 * ────────────────
 * createPublicWs / createPrivateWs both implement an exponential back-off
 * reconnect loop (1 s → 2 s → 4 s … up to 30 s).  After every successful
 * reconnect, the optional `onReconnect` callback is fired so callers can
 * re-fetch REST state to catch any events that arrived while offline.
 *
 * Returns a handle object { close() } so the caller can tear it down on
 * component unmount or symbol change.
 */

import api from '../lib/axiosClient'

// ── REST call helpers ──────────────────────────────────────────────────────

export async function getWalletBalances() {
  const { data } = await api.get('/wallet/balances')
  return data
}

export async function getPositions() {
  const { data } = await api.get('/positions')
  return data
}

export async function getOpenOrders() {
  const { data } = await api.get('/orders', { params: { status: 'OPEN' } })
  return data
}

export async function getTradeHistory(page = 1, pageSize = 50) {
  const { data } = await api.get('/trades/history', {
    params: { page, page_size: pageSize },
  })
  return data
}

export async function approveOrder(orderId) {
  const { data } = await api.post(`/orders/${orderId}/approve`)
  return data
}

export async function panicClosePosition(positionId) {
  const { data } = await api.post(`/positions/${positionId}/close`)
  return data
}

export async function panicCancelOrder(orderId) {
  const { data } = await api.delete(`/orders/${orderId}`)
  return data
}

// ── Binance public REST (no auth / no backend proxy) ──────────────────────

/**
 * Fetch OHLCV candles directly from Binance's public REST API.
 * Returns an array ready for lightweight-charts: { time, open, high, low, close }
 * where `time` is a Unix timestamp in SECONDS.
 */
export async function fetchOhlcv(symbol = 'BTCUSDT', interval = '1m', limit = 100) {
  const url = `https://data-api.binance.vision/api/v3/klines?symbol=${encodeURIComponent(symbol)}&interval=${interval}&limit=${limit}`
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Binance klines fetch failed: ${res.status}`)
  const raw = await res.json()
  // Binance kline array: [openTime, open, high, low, close, ...]
  return raw
    .map((k) => {
      const ohlc = {
        time: Math.floor(k[0] / 1000),      // ms → seconds
        open:  parseFloat(k[1]),
        high:  parseFloat(k[2]),
        low:   parseFloat(k[3]),
        close: parseFloat(k[4]),
      }
      // Validate all fields are finite numbers
      const isValid = [ohlc.time, ohlc.open, ohlc.high, ohlc.low, ohlc.close].every(Number.isFinite)
      return isValid ? ohlc : null
    })
    .filter(Boolean)
}

// ── WebSocket factory helpers ──────────────────────────────────────────────

const MIN_BACKOFF_MS = 1_000
const MAX_BACKOFF_MS = 30_000

/**
 * Internal: exponential back-off reconnect loop.
 *
 * @param {() => WebSocket}  factory      creates a new WS connection
 * @param {Record}           handlers     { onmessage, onerror? }
 * @param {() => void}       onReconnect  called after a successful reconnect
 * @param {{ current: bool }} mountedRef  set to false on teardown
 * @returns {{ close() }}
 */
function _createResilientWs(factory, handlers, onReconnect, mountedRef) {
  let ws = null
  let backoff = MIN_BACKOFF_MS
  let reconnectTimer = null
  let manualClose = false

  function connect(isReconnect = false) {
    if (!mountedRef.current) return
    ws = factory()

    ws.onopen = () => {
      backoff = MIN_BACKOFF_MS   // reset backoff on successful connection
      if (isReconnect && typeof onReconnect === 'function') {
        onReconnect()
      }
    }

    ws.onmessage = handlers.onmessage || null

    ws.onerror = (err) => {
      if (typeof handlers.onerror === 'function') handlers.onerror(err)
    }

    ws.onclose = () => {
      if (manualClose || !mountedRef.current) return
      console.warn(`[LiveWS] Disconnected — reconnecting in ${backoff}ms…`)
      reconnectTimer = setTimeout(() => {
        backoff = Math.min(backoff * 2, MAX_BACKOFF_MS)
        connect(true)
      }, backoff)
    }
  }

  connect(false)

  return {
    close() {
      manualClose = true
      clearTimeout(reconnectTimer)
      if (ws) {
        ws.onclose = null  // prevent reconnect logic from firing
        ws.close()
      }
    },
  }
}

/**
 * Create a resilient public WebSocket connection to the backend market stream.
 *
 * @param {string}    wsBase         e.g. "ws://localhost:8000/api/v1"
 * @param {object}    handlers       { onmessage(event), onerror?(event) }
 * @param {Function}  onReconnect    called after reconnect — use to re-sync REST data
 * @param {{ current: bool }} mountedRef
 * @returns {{ close() }}
 */
export function createPublicWs(wsBase, handlers, onReconnect, mountedRef) {
  return _createResilientWs(
    () => new WebSocket(`${wsBase}/ws/market`),
    handlers,
    onReconnect,
    mountedRef,
  )
}

/**
 * Create a resilient private WebSocket connection for order / approval events.
 *
 * @param {string}    wsBase
 * @param {string}    token          Supabase access token
 * @param {object}    handlers       { onmessage(event), onerror?(event) }
 * @param {Function}  onReconnect
 * @param {{ current: bool }} mountedRef
 * @returns {{ close() }}
 */
export function createPrivateWs(wsBase, token, handlers, onReconnect, mountedRef) {
  return _createResilientWs(
    () => new WebSocket(`${wsBase}/ws/private?token=${encodeURIComponent(token)}`),
    handlers,
    onReconnect,
    mountedRef,
  )
}
