import { scanApi } from '@/services/api'

export async function fetchResult(scanId: string) {
  const { data } = await scanApi.result(scanId)
  return data.result
}

export async function fetchTechnical(scanId: string) {
  const { data } = await scanApi.technical(scanId)
  return data.technical
}

export async function fetchExplanation(scanId: string) {
  const { data } = await scanApi.explanation(scanId)
  return data.explanation
}
