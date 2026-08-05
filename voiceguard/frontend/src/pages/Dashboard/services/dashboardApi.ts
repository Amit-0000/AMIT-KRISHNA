import { api, scanApi } from '@/services/api'
import type { DashboardData } from '../types'
import type { ScanResult } from '@/types'

export async function fetchDashboardData(): Promise<DashboardData> {
  const { data } = await api.get<DashboardData>('/dashboard')
  return data
}

export async function fetchRecentScans(): Promise<ScanResult[]> {
  const { data } = await api.get<ScanResult[]>('/dashboard/recent-scans')
  return data
}

export async function deleteScan(scanId: string): Promise<void> {
  await scanApi.delete(scanId)
}
