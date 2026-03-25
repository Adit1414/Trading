import { useQuery } from '@tanstack/react-query'
import api from '../lib/axiosClient'

/**
 * GET /strategies
 * Returns: StrategyDB[] → { id, name, type_code, parameter_schema, description }
 */
export function useStrategies() {
  return useQuery({
    queryKey: ['strategies'],
    queryFn: async () => {
      const { data } = await api.get('/strategies')
      console.log('[useStrategies] Fetched strategies:', data)
      return data
    },
    staleTime: 5 * 60 * 1000, // 5 min — strategies rarely change
    retry: 2,
  })
}
