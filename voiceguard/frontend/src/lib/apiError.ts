import { isAxiosError } from 'axios'
import type { ApiError, ApiErrorDetail } from '@/types'

export interface ParsedApiError {
  code: string
  message: string
  details: ApiErrorDetail[]
  status: number | null
  retryAfter: number | null
}

const FALLBACK_MESSAGE = 'Something went wrong. Please try again.'

export function parseApiError(error: unknown): ParsedApiError {
  if (isAxiosError<{ error?: ApiError }>(error)) {
    const payload = error.response?.data?.error
    const retryAfterHeader = error.response?.headers['retry-after']
    return {
      code: payload?.code ?? 'UNKNOWN_ERROR',
      message: payload?.message ?? FALLBACK_MESSAGE,
      details: payload?.details ?? [],
      status: error.response?.status ?? null,
      retryAfter: retryAfterHeader ? Number(retryAfterHeader) : null,
    }
  }
  return { code: 'UNKNOWN_ERROR', message: FALLBACK_MESSAGE, details: [], status: null, retryAfter: null }
}
