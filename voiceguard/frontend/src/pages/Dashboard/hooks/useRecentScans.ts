import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchRecentScans, deleteScan } from '../services/dashboardApi'
import type { ScanResult } from '@/types'
import type { SortField, SortDir } from '../types'

const PAGE_SIZE = 10

export function useRecentScans() {
  const qc = useQueryClient()
  const [search, setSearch] = useState('')
  const [sortBy, setSortBy] = useState<SortField>('created_at')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [page, setPage] = useState(1)

  const query = useQuery({
    queryKey: ['dashboard', 'recent-scans'],
    queryFn: fetchRecentScans,
    staleTime: 30_000,
  })

  const deleteMutation = useMutation({
    mutationFn: deleteScan,
    onMutate: async (scanId: string) => {
      await qc.cancelQueries({ queryKey: ['dashboard', 'recent-scans'] })
      const prev = qc.getQueryData<ScanResult[]>(['dashboard', 'recent-scans'])
      qc.setQueryData<ScanResult[]>(
        ['dashboard', 'recent-scans'],
        (old) => old?.filter((s) => s.scan_id !== scanId) ?? []
      )
      return { prev }
    },
    onError: (_err, _id, ctx) => {
      if (ctx?.prev) {
        qc.setQueryData(['dashboard', 'recent-scans'], ctx.prev)
      }
    },
  })

  const sortToggle = (field: SortField) => {
    if (sortBy === field) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortBy(field)
      setSortDir('desc')
    }
    setPage(1)
  }

  const filtered = useMemo(() => {
    const scans = query.data ?? []
    const q = search.trim().toLowerCase()
    const out = q
      ? scans.filter(
          (s) =>
            s.file_name.toLowerCase().includes(q) ||
            s.verdict.toLowerCase().includes(q)
        )
      : scans

    return [...out].sort((a, b) => {
      let cmp = 0
      switch (sortBy) {
        case 'file_name':
          cmp = a.file_name.localeCompare(b.file_name)
          break
        case 'verdict':
          cmp = a.verdict.localeCompare(b.verdict)
          break
        case 'confidence':
          cmp = a.confidence - b.confidence
          break
        case 'inference_time_ms':
          cmp = a.inference_time_ms - b.inference_time_ms
          break
        case 'created_at':
        default:
          cmp = new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      }
      return sortDir === 'asc' ? cmp : -cmp
    })
  }, [query.data, search, sortBy, sortDir])

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const paginated = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  return {
    scans: paginated,
    allScans: query.data ?? [],
    filteredCount: filtered.length,
    isLoading: query.isLoading,
    isError: query.isError,
    refetch: query.refetch,
    search,
    setSearch: (v: string) => { setSearch(v); setPage(1) },
    sortBy,
    sortDir,
    sortToggle,
    page,
    setPage,
    totalPages,
    pageSize: PAGE_SIZE,
    deleteOne: deleteMutation.mutate,
    isDeleting: deleteMutation.isPending,
  }
}
