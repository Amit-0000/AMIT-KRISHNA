export interface HelpArticle {
  slug: string
  title: string
  category: string
  summary: string
  body: string[]
}

export const HELP_CATEGORIES = [
  'Getting started',
  'Uploads & scanning',
  'Understanding results',
  'Account & privacy',
  'Troubleshooting',
] as const

export const HELP_ARTICLES: HelpArticle[] = [
  {
    slug: 'how-voiceguard-detects-ai-audio',
    title: 'How VoiceGuard detects AI-generated audio',
    category: 'Getting started',
    summary: 'A quick tour of the detection pipeline, from upload to verdict.',
    body: [
      'VoiceGuard analyzes an audio file with a forensic classifier trained to tell genuine human speech apart from AI-generated or synthetic speech (deepfakes, text-to-speech, and voice conversion).',
      'When you upload a file, VoiceGuard extracts acoustic features, runs them through its detection model, and returns a verdict — Human, AI-generated, or Uncertain — along with a confidence score.',
      'Uncertain means the model\'s confidence fell below its decision threshold. Treat uncertain results as inconclusive rather than as a "probably human" or "probably AI" signal.',
      'Every result includes technical details (raw model scores, decision threshold, model version) and an explanation panel highlighting which parts of the audio most influenced the verdict.',
    ],
  },
  {
    slug: 'supported-audio-formats',
    title: 'Supported audio formats and file limits',
    category: 'Uploads & scanning',
    summary: 'What file types, sizes, and lengths VoiceGuard accepts.',
    body: [
      'VoiceGuard accepts WAV, MP3, FLAC, M4A, OGG, and AIFF files.',
      'Files must be 10 MB or smaller. If your file is larger, try re-exporting it at a lower bitrate or trimming it to the relevant segment.',
      'There is no hard limit on duration, but files longer than about 10 minutes may take noticeably longer to process — for best results, upload a focused clip rather than a full-length recording.',
      'If your file is rejected, VoiceGuard will tell you exactly why (wrong format, too large, or an unreadable/corrupt file) so you can fix it and try again.',
    ],
  },
  {
    slug: 'understanding-your-scan-result',
    title: 'Understanding your scan result',
    category: 'Understanding results',
    summary: 'What the verdict card, confidence score, and technical details mean.',
    body: [
      'The verdict card shows VoiceGuard\'s overall call — Likely human, Likely AI-generated, or Uncertain — with a confidence percentage.',
      'The explanation panel lists the audio regions that most influenced the verdict, ranked by importance, along with any warnings the model flagged (for example, heavy compression or background noise that can affect accuracy).',
      'Technical details (expandable below the explanation) show the raw model scores, the decision threshold used, the model and feature-extractor versions, and a per-stage timing breakdown of the pipeline.',
      'A result is a statistical signal, not a legal or forensic certification — always use judgment, especially on borderline (uncertain) results.',
    ],
  },
  {
    slug: 'tracking-scan-status',
    title: 'Tracking scan status and history',
    category: 'Uploads & scanning',
    summary: 'What each status in your History table means, and how to manage scans.',
    body: [
      'Every file you submit moves through a pipeline: queued → preprocessing → ready for AI → running inference → completed (or failed at any step).',
      'Open History to see every scan you\'ve submitted, filter by status, and sort by upload date. Click any row to see its full detail.',
      'While a scan is still processing you can cancel it. Once a scan is finished — completed, failed, cancelled, or expired — you can delete it to remove it from your history.',
      'If a scan fails, the error message on its detail page explains what went wrong (for example, model unavailable or a processing error) — most failures are transient and worth retrying with the same file.',
    ],
  },
  {
    slug: 'data-privacy-and-retention',
    title: 'Your data and privacy',
    category: 'Account & privacy',
    summary: 'How long VoiceGuard keeps your audio, and what it\'s used for.',
    body: [
      'Your uploaded audio is deleted within 60 seconds of analysis completing — it is not stored permanently on VoiceGuard\'s servers.',
      'Your audio is never used to train VoiceGuard\'s models or anyone else\'s. It exists only long enough to produce your result.',
      'Every result discloses the model\'s known limitations directly on the page (via the explanation panel\'s warnings) rather than hiding them — so you always know how much to trust a given verdict.',
      'Account data (your email, display name, and scan history metadata — not audio) is retained so you can review past results. You can change your password at any time from Settings → Account.',
    ],
  },
  {
    slug: 'changing-your-password',
    title: 'Changing your password',
    category: 'Account & privacy',
    summary: 'Update your credentials from the Account settings page.',
    body: [
      'Go to Settings → Account and use the "Change password" form. You\'ll need your current password and a new one that meets VoiceGuard\'s strength requirements (at least 8 characters, with uppercase, lowercase, a number, and a special character).',
      'Changing your password immediately signs you out of every other device and session — you\'ll need to log in again there with the new password.',
      'If you\'re signed out and can\'t remember your current password, use "Forgot password" on the login page instead.',
    ],
  },
  {
    slug: 'why-was-my-file-rejected',
    title: 'Why was my file rejected?',
    category: 'Troubleshooting',
    summary: 'Common upload errors and how to fix them.',
    body: [
      'VoiceGuard checks every file for three things before accepting it: file type, file size, and whether the file is readable.',
      'Unsupported format: only WAV, MP3, FLAC, M4A, OGG, and AIFF are accepted. Re-export your file to one of these formats.',
      'File too large: files must be 10 MB or smaller. Re-encode at a lower bitrate or trim the clip.',
      'Corrupt or unreadable file: the file may be truncated or use an unsupported codec inside a supported container. Try re-exporting it from the original source.',
      'If none of these apply and your file is still being rejected, use Give Feedback to report it — include the file format and approximate size.',
    ],
  },
  {
    slug: 'scan-stuck-or-slow',
    title: 'My scan seems stuck or slow',
    category: 'Troubleshooting',
    summary: 'What to do if a scan is taking longer than expected.',
    body: [
      'Most scans complete within a couple of minutes. Longer files or a busy queue can extend that.',
      'The scan detail page auto-refreshes while a scan is in progress, so you don\'t need to reload manually.',
      'If a scan has been stuck on the same step for an unusually long time, cancel it from History and start a new scan with the same file — this resolves the vast majority of stalls.',
      'If it happens repeatedly, use Give Feedback and mention the scan\'s file name and roughly when you uploaded it.',
    ],
  },
]

export function getArticleBySlug(slug: string): HelpArticle | undefined {
  return HELP_ARTICLES.find((a) => a.slug === slug)
}

export function getRelatedArticles(article: HelpArticle, limit = 3): HelpArticle[] {
  return HELP_ARTICLES.filter((a) => a.slug !== article.slug && a.category === article.category).slice(0, limit)
}
