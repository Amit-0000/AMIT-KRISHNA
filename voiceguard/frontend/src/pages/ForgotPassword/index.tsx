import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Mail, MailCheck } from 'lucide-react'
import { toast } from 'sonner'
import { AuthLayout } from '@/components/layout/AuthLayout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { authApi } from '@/services/api'
import { parseApiError } from '@/lib/apiError'
import { emailSchema } from '@/lib/validation'

const forgotPasswordSchema = z.object({ email: emailSchema })
type ForgotPasswordFormValues = z.infer<typeof forgotPasswordSchema>

export function ForgotPasswordPage() {
  const [submitted, setSubmitted] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordFormValues>({
    resolver: zodResolver(forgotPasswordSchema),
    mode: 'onBlur',
    defaultValues: { email: '' },
  })

  async function onSubmit(values: ForgotPasswordFormValues) {
    try {
      await authApi.forgotPassword(values.email)
    } catch (err) {
      // Intentionally does not branch the UI on failure — the backend never
      // reveals whether an email exists, to prevent account enumeration.
      const parsed = parseApiError(err)
      if (parsed.status === 429) {
        toast.error(parsed.message)
        return
      }
    } finally {
      setSubmitted(true)
    }
  }

  if (submitted) {
    return (
      <AuthLayout title="Check your email">
        <div className="flex flex-col items-center text-center gap-4">
          <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-brand-muted border border-brand-border">
            <MailCheck className="w-7 h-7 text-brand" aria-hidden="true" />
          </div>
          <p className="text-sm text-text-secondary">
            If an account exists for that email, we've sent a link to reset your password.
          </p>
          <Button asChild variant="secondary" className="w-full">
            <Link to="/login">Back to login</Link>
          </Button>
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout
      title="Forgot your password?"
      description="Enter your email and we'll send you a reset link."
      footer={
        <Link to="/login" className="text-brand hover:text-brand-light font-medium">
          Back to login
        </Link>
      }
    >
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
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

        <Button type="submit" className="w-full" size="lg" loading={isSubmitting}>
          Send reset link
        </Button>
      </form>
    </AuthLayout>
  )
}
