import api from '../lib/axiosClient'

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
