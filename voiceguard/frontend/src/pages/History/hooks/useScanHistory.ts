import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { scanApi } from '@/services/api'
import type { ScanRecordStatus } from '@/types'

const PAGE_SIZE = 10
const QUERY_KEY = 'scan-history'

export function useScanHistory() {
  const qc = useQueryClient()
  const [page, setPageState] = useState(1)
  const [statusFilter, setStatusFilterState] = useState<ScanRecordStatus | 'all'>('all')
  const [sort, setSort] = useState<'created_at' | '-created_at'>('-created_at')

  const query = useQuery({
    queryKey: [QUERY_KEY, page, statusFilter, sort],
    queryFn: async () => {
      const { data } = await scanApi.history({
        page,
        page_size: PAGE_SIZE,
        sort,
        ...(statusFilter !== 'all' ? { status: statusFilter } : {}),
      })
      return data
    },
    staleTime: 15_000,
  })

  const invalidate = () => qc.invalidateQueries({ queryKey: [QUERY_KEY] })

  const cancelMutation = useMutation({
    mutationFn: (scanId: string) => scanApi.cancel(scanId),
    onSuccess: invalidate,
  })

  const deleteMutation = useMutation({
    mutationFn: (scanId: string) => scanApi.delete(scanId),
    onSuccess: invalidate,
  })

  function setPage(next: number) {
    setPageState(Math.max(1, next))
  }

  function setStatusFilter(next: ScanRecordStatus | 'all') {
    setStatusFilterState(next)
    setPageState(1)
  }

  function toggleSort() {
    setSort((s) => (s === '-created_at' ? 'created_at' : '-created_at'))
    setPageState(1)
  }

  return {
    scans: query.data?.scans ?? [],
    total: query.data?.total ?? 0,
    totalPages: query.data?.total_pages ?? 1,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    isError: query.isError,
    refetch: query.refetch,
    page,
    setPage,
    pageSize: PAGE_SIZE,
    statusFilter,
    setStatusFilter,
    sort,
    toggleSort,
    cancelScan: cancelMutation.mutate,
    cancellingId: cancelMutation.variables,
    isCancelling: cancelMutation.isPending,
    deleteScan: deleteMutation.mutate,
    deletingId: deleteMutation.variables,
    isDeleting: deleteMutation.isPending,
  }
}
