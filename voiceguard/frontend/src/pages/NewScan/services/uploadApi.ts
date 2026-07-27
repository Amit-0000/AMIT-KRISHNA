import { scanApi } from '@/services/api'
import type { ScanResult } from '@/types'

export interface UploadResult {
  scan_id: string
}

export async function submitScan(
  file: File,
  onProgress: (pct: number) => void
): Promise<UploadResult> {
  const { data } = await scanApi.upload(file, onProgress)
  return { scan_id: data.scan_id }
}

export async function getScanStatus(scanId: string): Promise<ScanResult> {
  const { data } = await scanApi.status(scanId)
  return data
}
