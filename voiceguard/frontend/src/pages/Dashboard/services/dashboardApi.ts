import { api, scanApi } from '@/services/api'
import type {
  DashboardData,
  DashboardStats,
  TrendDataPoint,
  ConfidenceBucket,
  ActivityItem,
  ModelStatus,
} from '../types'
import type { ScanResult } from '@/types'

// ─── Mock data generators ─────────────────────────────────────────────────────

function mockTrend(): TrendDataPoint[] {
  const points: TrendDataPoint[] = []
  const now = new Date()
  const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

  for (let i = 29; i >= 0; i--) {
    const d = new Date(now)
    d.setDate(d.getDate() - i)
    const isWeekend = d.getDay() === 0 || d.getDay() === 6
    const base = isWeekend ? 2 : 5
    const ai = Math.round(base * (0.5 + Math.random() * 0.6))
    const human = Math.round(base * (0.3 + Math.random() * 0.5))
    const uncertain = Math.round(base * 0.1 * Math.random())
    points.push({
      date: `${MONTHS[d.getMonth()]} ${d.getDate()}`,
      total: ai + human + uncertain,
      ai_generated: ai,
      human,
      uncertain,
    })
  }
  return points
}

function mockConfidenceDist(): ConfidenceBucket[] {
  const buckets: ConfidenceBucket[] = [
    { range: '0–10%',  min: 0,  max: 10,  count: 1,  zone: 'uncertain'  },
    { range: '10–20%', min: 10, max: 20,  count: 2,  zone: 'uncertain'  },
    { range: '20–30%', min: 20, max: 30,  count: 3,  zone: 'uncertain'  },
    { range: '30–40%', min: 30, max: 40,  count: 4,  zone: 'uncertain'  },
    { range: '40–50%', min: 40, max: 50,  count: 5,  zone: 'uncertain'  },
    { range: '50–60%', min: 50, max: 60,  count: 8,  zone: 'uncertain'  },
    { range: '60–70%', min: 60, max: 70,  count: 6,  zone: 'borderline' },
    { range: '70–80%', min: 70, max: 80,  count: 9,  zone: 'borderline' },
    { range: '80–90%', min: 80, max: 90,  count: 18, zone: 'definitive' },
    { range: '90–100%',min: 90, max: 100, count: 72, zone: 'definitive' },
  ]
  return buckets
}

function mockActivity(): ActivityItem[] {
  const now = Date.now()
  return [
    {
      id: 'a1',
      type: 'scan_complete',
      title: 'Scan complete',
      description: 'voice_message_leak.wav — AI Generated · 91.4%',
      timestamp: new Date(now - 8 * 60 * 1000).toISOString(),
      verdict: 'ai_generated',
      scan_id: 'scan-001',
    },
    {
      id: 'a2',
      type: 'scan_complete',
      title: 'Scan complete',
      description: 'ceo_interview.mp3 — Human · 96.2%',
      timestamp: new Date(now - 2.5 * 60 * 60 * 1000).toISOString(),
      verdict: 'human',
      scan_id: 'scan-002',
    },
    {
      id: 'a3',
      type: 'feedback_submitted',
      title: 'Feedback recorded',
      description: 'You corrected the verdict for anonymous_call.wav',
      timestamp: new Date(now - 5 * 60 * 60 * 1000).toISOString(),
    },
    {
      id: 'a4',
      type: 'scan_complete',
      title: 'Scan complete',
      description: 'podcast_clip.flac — Uncertain · 58.7%',
      timestamp: new Date(now - 24 * 60 * 60 * 1000).toISOString(),
      verdict: 'uncertain',
      scan_id: 'scan-003',
    },
    {
      id: 'a5',
      type: 'model_updated',
      title: 'Model updated',
      description: 'LCNN upgraded to v2.1.0 — improved codec resistance',
      timestamp: new Date(now - 3 * 24 * 60 * 60 * 1000).toISOString(),
    },
    {
      id: 'a6',
      type: 'scan_complete',
      title: 'Scan complete',
      description: 'witness_statement.wav — Human · 88.3%',
      timestamp: new Date(now - 4 * 24 * 60 * 60 * 1000).toISOString(),
      verdict: 'human',
      scan_id: 'scan-004',
    },
  ]
}

function mockModelStatus(): ModelStatus {
  return {
    version: 'v2.1.0',
    health: 'healthy',
    eer_pct: 7.07,
    avg_inference_ms: 234,
    last_checked: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
    uptime_pct: 99.8,
    parameters: 699938,
  }
}

function mockStats(): DashboardStats {
  return {
    total_scans: 128,
    ai_detected: 72,
    human_verified: 48,
    uncertain: 8,
    avg_processing_ms: 234,
    scans_today: 3,
    scan_limit_daily: 50,
    reset_in_hours: 14,
  }
}

function mockRecentScans(): ScanResult[] {
  const files = [
    { name: 'voice_message_leak.wav', verdict: 'ai_generated' as const, conf: 91.4, dur: 8.3, ms: 201 },
    { name: 'ceo_interview.mp3',       verdict: 'human'        as const, conf: 96.2, dur: 42.1,ms: 312 },
    { name: 'podcast_clip.flac',       verdict: 'uncertain'    as const, conf: 58.7, dur: 120.0,ms:198},
    { name: 'witness_statement.wav',   verdict: 'human'        as const, conf: 88.3, dur: 15.6, ms: 267 },
    { name: 'synthetic_demo.mp3',      verdict: 'ai_generated' as const, conf: 97.1, dur: 5.0,  ms: 178 },
    { name: 'phone_call_anon.wav',     verdict: 'ai_generated' as const, conf: 83.6, dur: 22.4, ms: 289 },
    { name: 'live_news_clip.mp4',      verdict: 'human'        as const, conf: 91.8, dur: 35.2, ms: 321 },
    { name: 'deepfake_test_01.wav',    verdict: 'ai_generated' as const, conf: 94.5, dur: 6.7,  ms: 187 },
    { name: 'interview_excerpt.ogg',   verdict: 'human'        as const, conf: 78.4, dur: 28.9, ms: 254 },
    { name: 'voice_clone_sample.wav',  verdict: 'ai_generated' as const, conf: 89.2, dur: 10.1, ms: 211 },
    { name: 'press_conference.mp3',    verdict: 'human'        as const, conf: 93.7, dur: 180.0,ms: 340 },
    { name: 'audio_evidence_3b.wav',   verdict: 'uncertain'    as const, conf: 62.1, dur: 18.4, ms: 228 },
  ]

  return files.map((f, i) => ({
    scan_id: `scan-${String(i + 1).padStart(3, '0')}`,
    status: 'completed' as const,
    verdict: f.verdict,
    confidence: f.conf,
    human_score: f.verdict === 'human' ? f.conf : 100 - f.conf,
    ai_score: f.verdict === 'ai_generated' ? f.conf : 100 - f.conf,
    inference_time_ms: f.ms,
    model_version: 'v2.1.0',
    segment_count: Math.ceil(f.dur / 3),
    frequency_heatmap: null,
    file_name: f.name,
    file_duration_seconds: f.dur,
    created_at: new Date(Date.now() - i * 4 * 60 * 60 * 1000).toISOString(),
    share_token: null,
    user_verdict: null,
  }))
}

// ─── API with mock fallback ───────────────────────────────────────────────────

export async function fetchDashboardData(): Promise<DashboardData> {
  try {
    const { data } = await api.get<DashboardData>('/dashboard')
    return data
  } catch {
    // Backend not connected yet — return mock data
    await new Promise((r) => setTimeout(r, 600)) // simulate network latency
    return {
      stats: mockStats(),
      trend: mockTrend(),
      confidence_distribution: mockConfidenceDist(),
      recent_activity: mockActivity(),
      model_status: mockModelStatus(),
    }
  }
}

export async function fetchRecentScans(): Promise<ScanResult[]> {
  try {
    const { data } = await scanApi.history(1, 20)
    return data.items
  } catch {
    await new Promise((r) => setTimeout(r, 400))
    return mockRecentScans()
  }
}

export async function deleteScan(scanId: string): Promise<void> {
  try {
    await scanApi.delete(scanId)
  } catch {
    // Silently fail in mock mode
  }
}
