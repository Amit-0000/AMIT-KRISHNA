import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ChevronRight,
  Clock,
  Lock,
  Newspaper,
  ShieldCheck,
  ShieldQuestion,
  UserX,
  Building2,
  Search,
} from 'lucide-react'
import { AuthLayout } from '@/components/layout/AuthLayout'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { useAuth } from '@/hooks/useAuth'
import { userApi } from '@/services/api'

const USE_CASES = [
  { id: 'journalism', label: 'Journalism & fact-checking', icon: Newspaper },
  { id: 'moderation', label: 'Content moderation', icon: ShieldCheck },
  { id: 'compliance', label: 'Enterprise & compliance', icon: Building2 },
  { id: 'curiosity', label: 'Personal curiosity', icon: Search },
] as const

const PRIVACY_ITEMS = [
  { icon: Clock, text: 'Audio deleted within 60 seconds of analysis' },
  { icon: Lock, text: 'Never stored permanently on our servers' },
  { icon: UserX, text: 'Never used as training data — ever' },
]

const STEPS = ['welcome', 'use-case', 'privacy'] as const
type Step = (typeof STEPS)[number]

export function OnboardingPage() {
  const navigate = useNavigate()
  const { user, setUser } = useAuth()
  const [step, setStep] = useState<Step>('welcome')
  const [useCase, setUseCase] = useState<string | null>(null)

  const stepIndex = STEPS.indexOf(step)

  function goNext() {
    const next = STEPS[stepIndex + 1]
    if (next) setStep(next)
  }

  async function finish() {
    if (user) setUser({ ...user, onboarding_completed: true })
    navigate('/dashboard', { replace: true })
    try {
      await userApi.completeOnboarding()
    } catch {
      /* best-effort — the local state update above already unblocks the OnboardingGuard */
    }
  }

  const titles: Record<Step, { title: string; description?: string }> = {
    welcome: {
      title: `Welcome${user?.display_name ? `, ${user.display_name}` : ''}`,
      description: 'A quick, three-step tour before your first scan.',
    },
    'use-case': {
      title: 'What brings you here?',
      description: 'This helps us tailor tips — it never limits what you can do.',
    },
    privacy: {
      title: 'Your privacy, by default',
      description: 'No setup required — this is how VoiceGuard treats every file you upload.',
    },
  }

  return (
    <AuthLayout {...titles[step]}>
      {/* Progress dots */}
      <div className="flex items-center justify-center gap-1.5 mb-6" aria-hidden="true">
        {STEPS.map((s, i) => (
          <span
            key={s}
            className={cn(
              'h-1.5 rounded-full transition-all duration-300',
              i === stepIndex ? 'w-6 bg-brand' : 'w-1.5 bg-white/15'
            )}
          />
        ))}
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={step}
          initial={{ opacity: 0, x: 12 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -12 }}
          transition={{ duration: 0.2, ease: [0.25, 0, 0, 1] }}
        >
          {step === 'welcome' && (
            <div className="text-center space-y-6">
              <div className="w-16 h-16 rounded-2xl bg-brand-muted border border-brand-border flex items-center justify-center mx-auto">
                <ShieldQuestion className="w-8 h-8 text-brand" aria-hidden="true" />
              </div>
              <p className="text-sm text-text-secondary leading-relaxed">
                VoiceGuard analyzes audio and tells you whether it's most likely human or AI-generated,
                with a confidence score and an explanation you can inspect.
              </p>
              <Button className="w-full gap-2" size="lg" onClick={goNext}>
                Get started
                <ChevronRight className="w-4 h-4" aria-hidden="true" />
              </Button>
            </div>
          )}

          {step === 'use-case' && (
            <div className="space-y-5">
              <div className="grid grid-cols-1 gap-2" role="radiogroup" aria-label="Primary use case">
                {USE_CASES.map(({ id, label, icon: Icon }) => (
                  <button
                    key={id}
                    role="radio"
                    aria-checked={useCase === id}
                    onClick={() => setUseCase(id)}
                    className={cn(
                      'flex items-center gap-3 rounded-lg border px-4 py-3 text-left text-sm font-medium transition-colors',
                      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand',
                      useCase === id
                        ? 'border-brand/50 bg-brand-muted text-brand'
                        : 'border-white/10 text-text-secondary hover:bg-white/5'
                    )}
                  >
                    <Icon className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
                    {label}
                  </button>
                ))}
              </div>
              <Button className="w-full gap-2" size="lg" disabled={!useCase} onClick={goNext}>
                Continue
                <ChevronRight className="w-4 h-4" aria-hidden="true" />
              </Button>
            </div>
          )}

          {step === 'privacy' && (
            <div className="space-y-6">
              <ul className="space-y-3" role="list">
                {PRIVACY_ITEMS.map(({ icon: Icon, text }) => (
                  <li key={text} className="flex items-center gap-3 rounded-lg bg-white/[0.02] border border-white/6 px-4 py-3">
                    <div className="w-8 h-8 rounded-lg bg-human-muted border border-human-border flex items-center justify-center flex-shrink-0">
                      <Icon className="w-4 h-4 text-human" aria-hidden="true" />
                    </div>
                    <span className="text-sm text-text-secondary">{text}</span>
                  </li>
                ))}
              </ul>
              <Button className="w-full gap-2" size="lg" onClick={finish}>
                Go to dashboard
                <ChevronRight className="w-4 h-4" aria-hidden="true" />
              </Button>
            </div>
          )}
        </motion.div>
      </AnimatePresence>
    </AuthLayout>
  )
}
