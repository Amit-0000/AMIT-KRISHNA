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
    return api.post<{ scan: import('@/types').ScanRecord }>('/scans', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (e.total && onProgress) onProgress(Math.round((e.loaded * 100) / e.total))
      },
    })
  },
  status: (scanId: string) => api.get<{ scan: import('@/types').ScanRecord }>(`/scans/${scanId}`),
  pollStatus: (scanId: string) =>
    api.get<{ scan: import('@/types').ScanRecordStatusOnly }>(`/scans/${scanId}/status`),
  history: (
    params: {
      page?: number
      page_size?: number
      status?: import('@/types').ScanRecordStatus
      sort?: 'created_at' | '-created_at'
    } = {}
  ) =>
    api.get<{ scans: import('@/types').ScanRecord[] } & import('@/types').ScanListMeta>('/scans', { params }),
  cancel: (scanId: string) => api.post<{ scan: import('@/types').ScanRecord }>(`/scans/${scanId}/cancel`),
  delete: (scanId: string) => api.delete(`/scans/${scanId}`),
  // ── AI Processing Pipeline (Vertical Slice 03) ────────────────────────────
  process: (scanId: string) => api.post(`/scans/${scanId}/process`),
  result: (scanId: string) => api.get<{ result: import('@/types').AIScanResult }>(`/scans/${scanId}/result`),
  technical: (scanId: string) =>
    api.get<{ technical: import('@/types').AIScanTechnical }>(`/scans/${scanId}/technical`),
  explanation: (scanId: string) =>
    api.get<{ explanation: import('@/types').AIScanExplanation }>(`/scans/${scanId}/explanation`),
  // submitFeedback (per-scan verdict correction) has no backend route yet —
  // distinct from feedbackApi.submit (general product feedback) below, which
  // is live.
  submitFeedback: (scanId: string, verdict: import('@/types').Verdict) =>
    api.post(`/scans/${scanId}/feedback`, { user_verdict: verdict }),
  share: (scanId: string) =>
    api.post<{ share_url: string }>(`/scans/${scanId}/share`),
  // Public, unauthenticated lookup for the /r/:scanId shared-result page —
  // a separate route from result() above since it must not require the
  // owner's session. `scanId` here is really the opaque share token minted
  // by share() above, not the scan's own id.
  sharedResult: (scanId: string) =>
    api.get<{ result: import('@/types').AIScanResult }>(`/scans/shared/${scanId}`),
}

export const modelsApi = {
  list: () => api.get<{ models: import('@/types').ModelVersionInfo[] }>('/models'),
  current: () => api.get<{ model: Record<string, unknown> }>('/models/current'),
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

// ─── User / profile endpoints ─────────────────────────────────────────────────

export const userApi = {
  profile: () => api.get<{ user: import('@/types').User }>('/user/profile'),
  updateProfile: (display_name: string) =>
    api.patch<{ user: import('@/types').User }>('/user/profile', { display_name }),
  completeOnboarding: () =>
    api.patch<{ user: import('@/types').User }>('/user/profile', { onboarding_completed: true }),
  changePassword: (current_password: string, new_password: string) =>
    api.post('/user/change-password', { current_password, new_password }),
}

// ─── Feedback endpoints ────────────────────────────────────────────────────────
// General product feedback — distinct from scanApi.submitFeedback (per-scan
// verdict correction).

export const feedbackApi = {
  submit: (payload: { category: string; message: string; scan_id?: string; email?: string }) =>
    api.post('/feedback', payload),
}
