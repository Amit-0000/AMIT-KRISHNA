import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { AlertTriangle, Bug, CheckCircle2, Copy, Lightbulb, MessageSquare, ShieldAlert } from 'lucide-react'
import { PageContainer } from '@/components/layout/PageContainer'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'
import { parseApiError } from '@/lib/apiError'
import { feedbackApi } from '@/services/api'
import { useAuth } from '@/hooks/useAuth'

const CATEGORIES = [
  { value: 'incorrect_result', label: 'Incorrect result', icon: ShieldAlert },
  { value: 'bug', label: 'Bug report', icon: Bug },
  { value: 'feature_request', label: 'Feature request', icon: Lightbulb },
  { value: 'general', label: 'General feedback', icon: MessageSquare },
] as const

const feedbackSchema = z.object({
  category: z.enum(['incorrect_result', 'bug', 'feature_request', 'general']),
  message: z.string().trim().min(10, 'Please provide at least 10 characters').max(2000, 'Keep it under 2000 characters'),
  scanId: z.string().trim().optional(),
})

type FeedbackValues = z.infer<typeof feedbackSchema>

export function FeedbackPage() {
  const { user } = useAuth()
  const [searchParams] = useSearchParams()
  const [status, setStatus] = useState<'form' | 'success' | 'failed'>('form')
  const [lastMessage, setLastMessage] = useState('')

  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FeedbackValues>({
    resolver: zodResolver(feedbackSchema),
    defaultValues: {
      category: (searchParams.get('scanId') ? 'incorrect_result' : 'general') as FeedbackValues['category'],
      message: '',
      scanId: searchParams.get('scanId') ?? '',
    },
  })

  async function onSubmit(values: FeedbackValues) {
    try {
      await feedbackApi.submit({
        category: values.category,
        message: values.message,
        scan_id: values.scanId || undefined,
        email: user?.email,
      })
      setStatus('success')
      reset()
    } catch (err) {
      setLastMessage(values.message)
      const parsed = parseApiError(err)
      if (parsed.status && parsed.status !== 404) toast.error(parsed.message)
      setStatus('failed')
    }
  }

  async function copyMessage() {
    try {
      await navigator.clipboard.writeText(lastMessage)
      toast.success('Copied to clipboard')
    } catch {
      toast.error('Could not copy — select and copy the text manually.')
    }
  }

  if (status === 'success') {
    return (
      <PageContainer maxWidth="sm">
        <div className="card-base rounded-xl p-10 text-center">
          <div className="w-14 h-14 rounded-2xl bg-human-muted border border-human-border flex items-center justify-center mx-auto mb-5">
            <CheckCircle2 className="w-7 h-7 text-human" aria-hidden="true" />
          </div>
          <h1 className="text-heading-lg font-semibold text-text-primary mb-2">Thanks for the feedback</h1>
          <p className="text-sm text-text-secondary mb-6">
            We've received your message and will use it to improve VoiceGuard.
          </p>
          <div className="flex items-center justify-center gap-3">
            <Button variant="secondary" onClick={() => setStatus('form')}>
              Send another
            </Button>
            <Link to="/dashboard">
              <Button>Back to dashboard</Button>
            </Link>
          </div>
        </div>
      </PageContainer>
    )
  }

  if (status === 'failed') {
    return (
      <PageContainer maxWidth="sm">
        <div className="card-base rounded-xl p-10 text-center">
          <div className="w-14 h-14 rounded-2xl bg-uncertain-muted border border-uncertain-border flex items-center justify-center mx-auto mb-5">
            <AlertTriangle className="w-7 h-7 text-uncertain" aria-hidden="true" />
          </div>
          <h1 className="text-heading-lg font-semibold text-text-primary mb-2">Couldn't send that yet</h1>
          <p className="text-sm text-text-secondary mb-6">
            Feedback submission isn't wired up on our servers yet. Your message wasn't lost — copy it below and
            try again shortly, or hold onto it until this is live.
          </p>
          <div className="text-left text-sm text-text-secondary bg-white/[0.03] border border-white/8 rounded-lg p-4 mb-6 whitespace-pre-wrap">
            {lastMessage}
          </div>
          <div className="flex items-center justify-center gap-3">
            <Button variant="secondary" onClick={copyMessage} className="gap-2">
              <Copy className="w-3.5 h-3.5" aria-hidden="true" />
              Copy message
            </Button>
            <Button onClick={() => setStatus('form')}>Try again</Button>
          </div>
        </div>
      </PageContainer>
    )
  }

  return (
    <PageContainer
      maxWidth="sm"
      title="Give feedback"
      description="Report an issue, request a feature, or flag a result you think is wrong."
    >
      <form onSubmit={handleSubmit(onSubmit)} className="card-base rounded-xl p-6 space-y-5" noValidate>
        <div>
          <Label>What's this about?</Label>
          <Controller
            control={control}
            name="category"
            render={({ field }) => (
              <div role="radiogroup" aria-label="Feedback category" className="grid grid-cols-2 gap-2 mt-1.5">
                {CATEGORIES.map(({ value, label, icon: Icon }) => (
                  <button
                    key={value}
                    type="button"
                    role="radio"
                    aria-checked={field.value === value}
                    onClick={() => field.onChange(value)}
                    className={cn(
                      'flex items-center gap-2 rounded-lg border px-3 py-2.5 text-sm font-medium transition-colors text-left',
                      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand',
                      field.value === value
                        ? 'border-brand/50 bg-brand-muted text-brand'
                        : 'border-white/8 text-text-secondary hover:bg-white/5'
                    )}
                  >
                    <Icon className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
                    {label}
                  </button>
                ))}
              </div>
            )}
          />
        </div>

        <div>
          <Label htmlFor="message">Your message</Label>
          <div className="mt-1.5">
            <textarea
              id="message"
              rows={6}
              placeholder="What happened, and what did you expect instead?"
              className={cn(
                'flex w-full rounded-lg border bg-bg-elevated px-3 py-2 text-sm text-text-primary resize-none',
                'placeholder:text-text-tertiary transition-colors duration-150',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:border-brand/50',
                errors.message ? 'border-ai/50 focus-visible:ring-ai' : 'border-white/10 hover:border-white/20'
              )}
              aria-invalid={!!errors.message}
              aria-describedby={errors.message ? 'message-error' : undefined}
              {...register('message')}
            />
            {errors.message && (
              <p id="message-error" className="mt-1.5 text-xs text-ai" role="alert">
                {errors.message.message}
              </p>
            )}
          </div>
        </div>

        <div>
          <Label htmlFor="scanId">Related scan ID (optional)</Label>
          <div className="mt-1.5">
            <Input id="scanId" placeholder="e.g. 8f14e45f-ceea-..." {...register('scanId')} />
          </div>
        </div>

        <Button type="submit" className="w-full" size="lg" loading={isSubmitting}>
          Send feedback
        </Button>
      </form>
    </PageContainer>
  )
}
