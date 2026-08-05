import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Lock, CheckCircle2, XCircle } from 'lucide-react'
import { toast } from 'sonner'
import { AuthLayout } from '@/components/layout/AuthLayout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { authApi } from '@/services/api'
import { parseApiError } from '@/lib/apiError'
import { passwordSchema } from '@/lib/validation'
import { PasswordRequirements } from '@/pages/Signup/components/PasswordRequirements'

const resetPasswordSchema = z
  .object({
    password: passwordSchema,
    confirmPassword: z.string().min(1, 'Please confirm your password'),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  })

type ResetPasswordFormValues = z.infer<typeof resetPasswordSchema>

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')

  const [status, setStatus] = useState<'form' | 'success' | 'invalid-token'>(
    token ? 'form' : 'invalid-token'
  )

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<ResetPasswordFormValues>({
    resolver: zodResolver(resetPasswordSchema),
    mode: 'onBlur',
    defaultValues: { password: '', confirmPassword: '' },
  })

  const passwordValue = watch('password')

  async function onSubmit(values: ResetPasswordFormValues) {
    if (!token) return
    try {
      await authApi.resetPassword(token, values.password)
      setStatus('success')
    } catch (err) {
      const parsed = parseApiError(err)
      if (parsed.code === 'INVALID_TOKEN' || parsed.status === 400 || parsed.status === 404) {
        setStatus('invalid-token')
        return
      }
      toast.error(parsed.message)
    }
  }

  if (status === 'success') {
    return (
      <AuthLayout title="Password reset">
        <div className="flex flex-col items-center text-center gap-4">
          <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-human-muted border border-human-border">
            <CheckCircle2 className="w-7 h-7 text-human" aria-hidden="true" />
          </div>
          <p className="text-sm text-text-secondary">
            Your password has been reset. You can now log in with your new password.
          </p>
          <Button asChild className="w-full" size="lg">
            <Link to="/login">Continue to login</Link>
          </Button>
        </div>
      </AuthLayout>
    )
  }

  if (status === 'invalid-token') {
    return (
      <AuthLayout title="Reset link invalid" description="This link is invalid or has expired.">
        <div className="flex flex-col items-center text-center gap-4">
          <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-ai-muted border border-ai-border">
            <XCircle className="w-7 h-7 text-ai" aria-hidden="true" />
          </div>
          <Button asChild variant="secondary" className="w-full">
            <Link to="/forgot-password">Request a new link</Link>
          </Button>
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout title="Set a new password" description="Choose a strong password for your account.">
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
        <div>
          <Label htmlFor="password">New password</Label>
          <div className="mt-1.5">
            <Input
              id="password"
              type="password"
              autoComplete="new-password"
              autoFocus
              leftIcon={<Lock className="h-4 w-4" />}
              aria-invalid={!!errors.password}
              aria-describedby="password-requirements"
              error={errors.password?.message}
              {...register('password')}
            />
          </div>
          <PasswordRequirements password={passwordValue ?? ''} />
        </div>

        <div>
          <Label htmlFor="confirmPassword">Confirm new password</Label>
          <div className="mt-1.5">
            <Input
              id="confirmPassword"
              type="password"
              autoComplete="new-password"
              leftIcon={<Lock className="h-4 w-4" />}
              aria-invalid={!!errors.confirmPassword}
              aria-describedby={errors.confirmPassword ? 'confirmPassword-error' : undefined}
              error={errors.confirmPassword?.message}
              {...register('confirmPassword')}
            />
          </div>
        </div>

        <Button type="submit" className="w-full" size="lg" loading={isSubmitting}>
          Reset password
        </Button>
      </form>
    </AuthLayout>
  )
}
