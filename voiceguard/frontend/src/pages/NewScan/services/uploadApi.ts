import { scanApi } from '@/services/api'
import type { ScanRecord } from '@/types'

export interface UploadResult {
  scan_id: string
}

export async function submitScan(
  file: File,
  onProgress: (pct: number) => void
): Promise<UploadResult> {
  const { data } = await scanApi.upload(file, onProgress)
  return { scan_id: data.scan.id }
}

export async function getScanStatus(scanId: string): Promise<ScanRecord> {
  const { data } = await scanApi.status(scanId)
  return data.scan
}
