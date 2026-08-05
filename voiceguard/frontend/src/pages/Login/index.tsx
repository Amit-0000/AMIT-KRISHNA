import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Mail, Lock } from 'lucide-react'
import { toast } from 'sonner'
import { AuthLayout } from '@/components/layout/AuthLayout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { authApi } from '@/services/api'
import { useAuthStore } from '@/store/authStore'
import { parseApiError } from '@/lib/apiError'
import { emailSchema } from '@/lib/validation'

const loginSchema = z.object({
  email: emailSchema,
  password: z.string().min(1, 'Password is required'),
})

type LoginFormValues = z.infer<typeof loginSchema>

type LoginError =
  | { kind: 'credentials'; message: string }
  | { kind: 'unverified'; message: string }
  | { kind: 'rate_limited'; message: string }
  | { kind: 'generic'; message: string }
  | null

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const setUser = useAuthStore((s) => s.setUser)

  const [formError, setFormError] = useState<LoginError>(null)
  const [resending, setResending] = useState(false)
  const [resent, setResent] = useState(false)

  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    mode: 'onBlur',
    defaultValues: { email: '', password: '' },
  })

  async function onSubmit(values: LoginFormValues) {
    setFormError(null)
    setResent(false)
    try {
      const { data } = await authApi.login(values.email, values.password)
      setUser(data.user)
      const from = (location.state as { from?: string } | null)?.from ?? '/dashboard'
      navigate(from, { replace: true })
    } catch (err) {
      const parsed = parseApiError(err)

      if (parsed.code === 'EMAIL_NOT_VERIFIED') {
        setFormError({ kind: 'unverified', message: 'Please verify your email before logging in.' })
        return
      }
      if (parsed.status === 401 || parsed.code === 'INVALID_CREDENTIALS') {
        setFormError({ kind: 'credentials', message: 'Incorrect email or password.' })
        return
      }
      if (parsed.status === 429) {
        const wait = parsed.retryAfter ? ` Try again in ${parsed.retryAfter}s.` : ''
        setFormError({ kind: 'rate_limited', message: `Too many attempts.${wait}` })
        return
      }

      setFormError({ kind: 'generic', message: parsed.message })
      toast.error(parsed.message)
    }
  }

  async function handleResend() {
    const email = getValues('email')
    if (!email) return
    setResending(true)
    try {
      await authApi.resendVerification(email)
      setResent(true)
    } catch (err) {
      toast.error(parseApiError(err).message)
    } finally {
      setResending(false)
    }
  }

  return (
    <AuthLayout
      title="Welcome back"
      description="Log in to continue to your dashboard."
      footer={
        <>
          Don't have an account?{' '}
          <Link to="/signup" className="text-brand hover:text-brand-light font-medium">
            Sign up
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
        {formError && (
          <div
            role="alert"
            className="rounded-lg border border-ai/25 bg-ai/10 px-4 py-3 text-sm text-ai"
          >
            <p>{formError.message}</p>
            {formError.kind === 'unverified' && (
              <button
                type="button"
                onClick={handleResend}
                disabled={resending || resent}
                className="mt-1.5 font-medium underline underline-offset-2 disabled:opacity-60 disabled:no-underline"
              >
                {resent ? 'Verification email sent' : resending ? 'Sending…' : 'Resend verification email'}
              </button>
            )}
          </div>
        )}

        <div>
          <Label htmlFor="email">Email</Label>
          <div className="mt-1.5">
            <Input
              id="email"
              type="email"
              autoComplete="email"
              autoFocus
              leftIcon={<Mail className="h-4 w-4" />}
              aria-invalid={!!errors.email}
              aria-describedby={errors.email ? 'email-error' : undefined}
              error={errors.email?.message}
              {...register('email')}
            />
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between">
            <Label htmlFor="password">Password</Label>
            <Link to="/forgot-password" className="text-xs text-brand hover:text-brand-light font-medium">
              Forgot password?
            </Link>
          </div>
          <div className="mt-1.5">
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              leftIcon={<Lock className="h-4 w-4" />}
              aria-invalid={!!errors.password}
              aria-describedby={errors.password ? 'password-error' : undefined}
              error={errors.password?.message}
              {...register('password')}
            />
          </div>
        </div>

        <Button type="submit" className="w-full" size="lg" loading={isSubmitting}>
          Log in
        </Button>
      </form>
    </AuthLayout>
  )
}
