import axios, { type AxiosError, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios'
import { Capacitor } from '@capacitor/core'
import { Preferences } from '@capacitor/preferences'
import type { ApiError } from '@/types'

// ─── Native (Capacitor Android) auth transport ───────────────────────────────
// The web app authenticates with httponly, SameSite=Strict cookies (see
// api/auth/service.py) — that only works because Vercel's rewrites make the
// browser see the frontend and API as same-origin. The Capacitor app's
// WebView runs on its own origin (https://localhost) and calls the Railway
// API cross-origin directly, so those cookies are accepted at login but
// never sent back on later requests. The backend additively returns raw
// access/refresh tokens in the JSON body for that origin (api/auth/router.py's
// _is_mobile_client) — this stores them and sends them back as
// Authorization: Bearer. None of this runs in the browser build.
export const isNativeApp = Capacitor.isNativePlatform()

const ACCESS_TOKEN_KEY = 'vg_access_token'
const REFRESH_TOKEN_KEY = 'vg_refresh_token'

export const nativeTokenStorage = {
  async getAccessToken(): Promise<string | null> {
    if (!isNativeApp) return null
    return (await Preferences.get({ key: ACCESS_TOKEN_KEY })).value
  },
  async getRefreshToken(): Promise<string | null> {
    if (!isNativeApp) return null
    return (await Preferences.get({ key: REFRESH_TOKEN_KEY })).value
  },
  async set(accessToken: string, refreshToken: string): Promise<void> {
    if (!isNativeApp) return
    await Preferences.set({ key: ACCESS_TOKEN_KEY, value: accessToken })
    await Preferences.set({ key: REFRESH_TOKEN_KEY, value: refreshToken })
  },
  async clear(): Promise<void> {
    if (!isNativeApp) return
    await Preferences.remove({ key: ACCESS_TOKEN_KEY })
    await Preferences.remove({ key: REFRESH_TOKEN_KEY })
  },
}

// Overridable at build time (see frontend/.env.production.example) — must be
// an absolute URL for native (there is no Vercel rewrite proxy inside the
// APK), never localhost/10.0.2.2 in a release build.
const NATIVE_API_ORIGIN = import.meta.env.VITE_API_BASE_URL || 'https://backend-production-65bb9.up.railway.app'

export const api = axios.create({
  baseURL: isNativeApp ? `${NATIVE_API_ORIGIN}/api/v1` : '/api/v1',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
})

// ─── Request interceptor ─────────────────────────────────────────────────────
api.interceptors.request.use(
  async (config) => {
    if (isNativeApp) {
      const token = await nativeTokenStorage.getAccessToken()
      if (token) config.headers.set('Authorization', `Bearer ${token}`)
    }
    return config
  },
  (error: AxiosError) => Promise.reject(error)
)

// Single in-flight refresh shared by every request that 401s at the same
// time, so a burst of concurrent requests after token expiry triggers one
// /auth/refresh call, not one per request.
let nativeRefreshInFlight: Promise<string | null> | null = null

async function refreshNativeSession(): Promise<string | null> {
  const refreshToken = await nativeTokenStorage.getRefreshToken()
  if (!refreshToken) return null
  try {
    const resp = await axios.post(
      `${NATIVE_API_ORIGIN}/api/v1/auth/refresh`,
      { refresh_token: refreshToken },
      { headers: { 'Content-Type': 'application/json' } }
    )
    const body = resp.data?.data ?? resp.data
    if (body?.access_token && body?.refresh_token) {
      await nativeTokenStorage.set(body.access_token, body.refresh_token)
      return body.access_token as string
    }
  } catch {
    // Falls through to clearing tokens below — refresh token is dead
    // (expired/revoked/reused), same as the web app's silent-refresh giving up.
  }
  await nativeTokenStorage.clear()
  return null
}

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
    // login/refresh responses carry raw tokens only for the native origin
    // (see _is_mobile_client server-side) — stash them for the request
    // interceptor above to attach as Authorization on every later call.
    if (isNativeApp) {
      const data = response.data as { access_token?: string; refresh_token?: string } | null
      if (data?.access_token && data?.refresh_token) {
        void nativeTokenStorage.set(data.access_token, data.refresh_token)
      }
    }
    return response
  },
  async (error: AxiosError<{ error?: ApiError }>) => {
    const status = error.response?.status
    const originalRequest = error.config as (InternalAxiosRequestConfig & { _retriedAfterRefresh?: boolean }) | undefined

    // Native has no refresh cookie for the backend to silently rotate
    // server-side (that's the whole reason bearer tokens exist here), so the
    // client has to do the expired-access-token -> refresh -> retry dance
    // itself. Web never reaches this branch (isNativeApp is false).
    if (status === 401 && isNativeApp && originalRequest && !originalRequest._retriedAfterRefresh) {
      originalRequest._retriedAfterRefresh = true
      nativeRefreshInFlight ??= refreshNativeSession().finally(() => {
        nativeRefreshInFlight = null
      })
      const newAccessToken = await nativeRefreshInFlight
      if (newAccessToken) {
        originalRequest.headers.set('Authorization', `Bearer ${newAccessToken}`)
        return api(originalRequest)
      }
      window.dispatchEvent(new CustomEvent('vg:unauthorized'))
      return Promise.reject(error)
    }

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
  logout: async () => {
    // Native has no logout cookie for the backend to revoke server-side
    // (see isNativeApp above) — send the refresh token explicitly so the
    // session is actually revoked, not just forgotten client-side.
    const refresh_token = isNativeApp ? await nativeTokenStorage.getRefreshToken() : null
    const resp = await api.post('/auth/logout', refresh_token ? { refresh_token } : undefined)
    await nativeTokenStorage.clear()
    return resp
  },
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
  share: (scanId: string) =>
    api.post<{ share_url: string; token: string; expires_at: string | null }>(`/scans/${scanId}/share`),
  unshare: (scanId: string) => api.delete(`/scans/${scanId}/share`),
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
  delete: (id: string) =>
    api.delete(`/notifications/${id}`),
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
// General product feedback, including per-scan verdict corrections — the
// Feedback page's "Incorrect result" category + optional scan ID field
// (pages/Feedback/index.tsx) is how a user reports a wrong verdict; there is
// no separate structured verdict-correction endpoint.

export const feedbackApi = {
  submit: (payload: { category: string; message: string; scan_id?: string; email?: string }) =>
    api.post('/feedback', payload),
}
