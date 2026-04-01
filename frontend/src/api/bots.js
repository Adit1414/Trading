import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../lib/axiosClient'

/**
 * GET /bots
 * Returns: list of active bots
 */
export function useBots() {
  return useQuery({
    queryKey: ['bots'],
    queryFn: async () => {
      const { data } = await api.get('/bots')
      console.log('[useBots] Fetched active bots:', data)
      return data
    },
    retry: 1,
  })
}

/**
 * POST /bots
 * Body: { strategy, symbol, timeframe, is_testnet, parameters, take_profit, stop_loss }
 * Returns: Bot info
 */
export function useCreateBot() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload) => {
      console.log('[useCreateBot] Sending payload:', payload)
      const { data } = await api.post('/bots', payload)
      console.log('[useCreateBot] Response:', data)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bots'] })
    },
  })
}

/**
 * PUT /bots/{bot_id}/state
 * Body: { targetState } (e.g. "PAUSED", "START", "STOP")
 * Returns: Bot info
 */
export function useUpdateBotState(botId) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ targetState, idempotencyKey }) => {
      console.log(`[useUpdateBotState ${botId}] Target state:`, targetState)
      const { data } = await api.put(
        `/bots/${botId}/state`,
        { state: targetState },
        {
          headers: {
            'Idempotency-Key': idempotencyKey,
          },
        }
      )
      console.log(`[useUpdateBotState ${botId}] Response:`, data)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bots'] })
    },
  })
}
