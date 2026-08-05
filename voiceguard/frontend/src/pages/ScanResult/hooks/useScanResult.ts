import { useQuery } from '@tanstack/react-query'
import { fetchExplanation, fetchResult, fetchTechnical } from '../services/resultApi'

export function useScanResult(scanId: string) {
  const resultQuery = useQuery({
    queryKey: ['scan-result', scanId],
    queryFn: () => fetchResult(scanId),
    retry: false,
  })

  return {
    result: resultQuery.data,
    isLoading: resultQuery.isLoading,
    isError: resultQuery.isError,
    error: resultQuery.error,
    refetch: resultQuery.refetch,
  }
}

export function useScanTechnical(scanId: string, enabled: boolean) {
  const query = useQuery({
    queryKey: ['scan-technical', scanId],
    queryFn: () => fetchTechnical(scanId),
    enabled,
    retry: false,
  })
  return { technical: query.data, isLoading: query.isLoading, isError: query.isError }
}

export function useScanExplanation(scanId: string, enabled: boolean) {
  const query = useQuery({
    queryKey: ['scan-explanation', scanId],
    queryFn: () => fetchExplanation(scanId),
    enabled,
    retry: false,
  })
  return { explanation: query.data, isLoading: query.isLoading, isError: query.isError }
}
