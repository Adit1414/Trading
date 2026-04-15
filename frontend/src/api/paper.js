import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../lib/axiosClient'

export function usePaperBots() {
  return useQuery({
    queryKey: ['paper', 'bots'],
    queryFn: async () => {
      const { data } = await api.get('/paper/bots')
      return data
    },
    refetchInterval: 10000,
  })
}

export function usePaperLedger() {
  return useQuery({
    queryKey: ['paper', 'ledger'],
    queryFn: async () => {
      const { data } = await api.get('/paper/ledger')
      return data
    },
    refetchInterval: 10000,
  })
}

export function usePaperPortfolio(tf = '1D') {
  return useQuery({
    queryKey: ['paper', 'portfolio', tf],
    queryFn: async () => {
      const { data } = await api.get(`/paper/portfolio?tf=${tf}`)
      return data
    },
    refetchInterval: 60000,
  })
}

export function useSubmitPaperKeys() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ api_key, secret }) => {
      const { data } = await api.post('/paper/keys', { api_key, secret })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['paper'] })
    },
  })
}

export function useRevokePaperKeys() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.delete('/paper/keys')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['paper'] })
    },
  })
}
