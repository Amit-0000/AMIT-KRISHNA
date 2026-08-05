import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { CheckCircle2, Loader2, XCircle } from 'lucide-react'
import { toast } from 'sonner'
import { AuthLayout } from '@/components/layout/AuthLayout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { authApi } from '@/services/api'
import { parseApiError } from '@/lib/apiError'

type Status = 'verifying' | 'success' | 'error' | 'missing-token'

export function VerifyEmailPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')

  const [status, setStatus] = useState<Status>(token ? 'verifying' : 'missing-token')
  const [resendEmail, setResendEmail] = useState('')
  const [resending, setResending] = useState(false)
  const [resent, setResent] = useState(false)
  const attempted = useRef(false)

  useEffect(() => {
    if (!token || attempted.current) return
    attempted.current = true

    authApi
      .verifyEmail(token)
      .then(() => setStatus('success'))
      .catch(() => setStatus('error'))
  }, [token])

  async function handleResend(e: React.FormEvent) {
    e.preventDefault()
    if (!resendEmail) return
    setResending(true)
    try {
      await authApi.resendVerification(resendEmail)
      setResent(true)
    } catch (err) {
      toast.error(parseApiError(err).message)
    } finally {
      setResending(false)
    }
  }

  if (status === 'verifying') {
    return (
      <AuthLayout title="Verifying your email">
        <div className="flex flex-col items-center gap-4 py-4" role="status" aria-label="Verifying email">
          <Loader2 className="h-8 w-8 text-brand animate-spin" aria-hidden="true" />
          <p className="text-sm text-text-secondary">Just a moment…</p>
        </div>
      </AuthLayout>
    )
  }

  if (status === 'success') {
    return (
      <AuthLayout title="Email verified">
        <div className="flex flex-col items-center text-center gap-4">
          <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-human-muted border border-human-border">
            <CheckCircle2 className="w-7 h-7 text-human" aria-hidden="true" />
          </div>
          <p className="text-sm text-text-secondary">
            Your email has been verified. You can now log in to your account.
          </p>
          <Button asChild className="w-full" size="lg">
            <Link to="/login">Continue to login</Link>
          </Button>
        </div>
      </AuthLayout>
    )
  }

  // 'error' (invalid/expired token) or 'missing-token'
  return (
    <AuthLayout
      title="Verification link invalid"
      description={
        status === 'missing-token'
          ? 'This link is missing a verification token.'
          : 'This link is invalid or has expired.'
      }
    >
      <div className="flex flex-col items-center text-center gap-4">
        <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-ai-muted border border-ai-border">
          <XCircle className="w-7 h-7 text-ai" aria-hidden="true" />
        </div>

        {resent ? (
          <p className="text-sm text-text-secondary">
            A new verification link has been sent to <span className="text-text-primary font-medium">{resendEmail}</span>.
          </p>
        ) : (
          <form onSubmit={handleResend} noValidate className="w-full space-y-3 text-left">
            <div>
              <Label htmlFor="resend-email">Resend verification link to</Label>
              <div className="mt-1.5">
                <Input
                  id="resend-email"
                  type="email"
                  autoComplete="email"
                  placeholder="you@example.com"
                  value={resendEmail}
                  onChange={(e) => setResendEmail(e.target.value)}
                  required
                />
              </div>
            </div>
            <Button type="submit" className="w-full" loading={resending} disabled={!resendEmail}>
              Resend link
            </Button>
          </form>
        )}

        <Link to="/login" className="text-sm text-brand hover:text-brand-light font-medium">
          Back to login
        </Link>
      </div>
    </AuthLayout>
  )
}
