import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../lib/axiosClient'

/**
 * GET /backtests?limit=N&offset=N
 * Returns: BacktestListItemDB[]
 */
export function useBacktests(limit = 20, offset = 0) {
  return useQuery({
    queryKey: ['backtests', limit, offset],
    queryFn: async () => {
      const { data } = await api.get('/backtests', {
        params: { limit, offset },
      })
      console.log('[useBacktests] Fetched backtests:', data)
      return data
    },
    retry: 1,
  })
}

/**
 * GET /backtests/{id}
 * Returns: BacktestDB (full detail including metrics, parameters)
 */
export function useBacktestDetail(id) {
  return useQuery({
    queryKey: ['backtests', id],
    queryFn: async () => {
      const { data } = await api.get(`/backtests/${id}`)
      console.log('[useBacktestDetail] Fetched:', data)
      return data
    },
    enabled: !!id,
    retry: 1,
  })
}

/**
 * POST /backtest/run
 * Body: BacktestRunRequest
 * Returns: BacktestRunResponse
 */
export function useRunBacktest() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload) => {
      console.log('[useRunBacktest] Sending payload:', payload)
      const { data } = await api.post('/backtest/run', payload)
      console.log('[useRunBacktest] Response:', data)
      return data
    },
    onSuccess: () => {
      // Refresh backtests list after successful run
      queryClient.invalidateQueries({ queryKey: ['backtests'] })
    },
  })
}
