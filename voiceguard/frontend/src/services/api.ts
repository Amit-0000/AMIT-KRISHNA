import axios, { type AxiosError, type AxiosResponse } from 'axios'
import type { ApiError } from '@/types'

export const api = axios.create({
  baseURL: '/api/v1',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
})

// ─── Request interceptor ─────────────────────────────────────────────────────
api.interceptors.request.use(
  (config) => config,
  (error: AxiosError) => Promise.reject(error)
)

// ─── Response interceptor ────────────────────────────────────────────────────
// The backend wraps every success response as { data: <payload> } (and, for
// paginated list endpoints, a sibling { meta: <pagination info> }) — see
// api/core/responses.py's success_envelope. Unwrapping it once here means
// every call site below (and every existing page consuming them) can treat
// response.data as the real payload directly, instead of each of them having
// to know about and re-implement `.data.data` unwrapping individually.
api.interceptors.response.use(
  (response: AxiosResponse) => {
    const body = response.data as unknown
    if (body && typeof body === 'object' && 'data' in (body as Record<string, unknown>)) {
      const envelope = body as { data: unknown; meta?: Record<string, unknown> }
      response.data =
        envelope.meta && typeof envelope.meta === 'object'
          ? { ...(envelope.data as object), ...envelope.meta }
          : envelope.data
    }
    return response
  },
  async (error: AxiosError<{ error?: ApiError }>) => {
    const status = error.response?.status

    if (status === 401) {
      // Token expired — clear auth state via store import-free approach
      window.dispatchEvent(new CustomEvent('vg:unauthorized'))
    }

    if (status === 429) {
      const retryAfter = error.response?.headers['retry-after']
      window.dispatchEvent(
        new CustomEvent('vg:rate-limited', { detail: { retryAfter } })
      )
    }

    return Promise.reject(error)
  }
)

// ─── Auth endpoints ───────────────────────────────────────────────────────────

export const authApi = {
  me: () => api.get<{ user: import('@/types').User }>('/auth/me'),
  logout: () => api.post('/auth/logout'),
  login: (email: string, password: string) =>
    api.post<{ user: import('@/types').User }>('/auth/login', { email, password }),
  signup: (email: string, password: string, display_name: string) =>
    api.post<{ user: import('@/types').User }>('/auth/register', {
      email,
      password,
      display_name,
    }),
  forgotPassword: (email: string) =>
    api.post('/auth/forgot-password', { email }),
  resetPassword: (token: string, password: string) =>
    api.post('/auth/reset-password', { token, password }),
  verifyEmail: (token: string) =>
    api.post('/auth/verify-email', { token }),
  resendVerification: (email: string) =>
    api.post('/auth/resend-verification', { email }),
}

// ─── Scan endpoints ──────────────────────────────────────────────────────────

export const scanApi = {
  upload: (file: File, onProgress?: (pct: number) => void) => {
    const form = new FormData()
    form.append('file', file)
    return api.post<{ scan_id: string }>('/scans', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (e.total && onProgress) onProgress(Math.round((e.loaded * 100) / e.total))
      },
    })
  },
  status: (scanId: string) =>
    api.get<import('@/types').ScanResult>(`/scans/${scanId}`),
  history: (page = 1, pageSize = 20) =>
    api.get<import('@/types').PaginatedResponse<import('@/types').ScanResult>>(
      '/scans',
      { params: { page, page_size: pageSize } }
    ),
  delete: (scanId: string) => api.delete(`/scans/${scanId}`),
  submitFeedback: (scanId: string, verdict: import('@/types').Verdict) =>
    api.post(`/scans/${scanId}/feedback`, { user_verdict: verdict }),
  share: (scanId: string) =>
    api.post<{ share_url: string }>(`/scans/${scanId}/share`),
}

// ─── Notification endpoints ───────────────────────────────────────────────────

export const notificationApi = {
  list: () =>
    api.get<import('@/types').AppNotification[]>('/notifications'),
  markRead: (id: string) =>
    api.patch(`/notifications/${id}/read`),
  markAllRead: () =>
    api.post('/notifications/mark-all-read'),
}
