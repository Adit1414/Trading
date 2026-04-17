import api from '../lib/axiosClient'

export async function getBinanceSettings() {
  const { data } = await api.get('/users/settings/binance')
  return data
}

export async function saveBinanceSettings(payload) {
  const { data } = await api.post('/users/settings/binance', payload)
  return data
}
