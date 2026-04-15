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

export function usePaperPortfolio() {
  return useQuery({
    queryKey: ['paper', 'portfolio'],
    queryFn: async () => {
      const { data } = await api.get('/paper/portfolio')
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
