import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { KeyRound, Lock, Mail, MailWarning, ShieldCheck } from 'lucide-react'
import { SettingsLayout } from './SettingsLayout'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { Separator } from '@/components/ui/separator'
import { passwordSchema } from '@/lib/validation'
import { parseApiError } from '@/lib/apiError'
import { formatDate } from '@/lib/utils'
import { authApi } from '@/services/api'
import { PasswordRequirements } from '@/pages/Signup/components/PasswordRequirements'
import { useProfile, useChangePassword } from './hooks/useProfile'

const changePasswordSchema = z
  .object({
    currentPassword: z.string().min(1, 'Enter your current password'),
    newPassword: passwordSchema,
    confirmPassword: z.string().min(1, 'Please confirm your new password'),
  })
  .refine((data) => data.newPassword === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  })

type ChangePasswordValues = z.infer<typeof changePasswordSchema>

function AccountSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-24 rounded-xl" />
      <Skeleton className="h-64 rounded-xl" />
    </div>
  )
}

export function AccountPage() {
  const { user, isLoading, isError, refetch } = useProfile()
  const changePassword = useChangePassword()
  const [resending, setResending] = useState(false)

  const {
    register,
    handleSubmit,
    reset,
    watch,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ChangePasswordValues>({
    resolver: zodResolver(changePasswordSchema),
    mode: 'onBlur',
    defaultValues: { currentPassword: '', newPassword: '', confirmPassword: '' },
  })

  const newPasswordValue = watch('newPassword')

  async function onSubmit(values: ChangePasswordValues) {
    try {
      await changePassword.mutateAsync({
        currentPassword: values.currentPassword,
        newPassword: values.newPassword,
      })
      toast.success('Password changed. Please log in again on your other devices.')
      reset()
    } catch (err) {
      const parsed = parseApiError(err)
      if (parsed.code === 'INVALID_CREDENTIALS') {
        setError('currentPassword', { type: 'server', message: 'Current password is incorrect.' })
        return
      }
      if (parsed.code === 'INVALID_PASSWORD') {
        setError('newPassword', { type: 'server', message: parsed.message })
        return
      }
      toast.error(parsed.message)
    }
  }

  async function handleResendVerification() {
    if (!user) return
    setResending(true)
    try {
      await authApi.resendVerification(user.email)
      toast.success('Verification email sent — check your inbox.')
    } catch (err) {
      toast.error(parseApiError(err).message)
    } finally {
      setResending(false)
    }
  }

  return (
    <SettingsLayout>
      <div className="space-y-6">
        <div>
          <h2 className="text-heading-lg font-semibold text-text-primary">Account</h2>
          <p className="text-sm text-text-secondary mt-1">
            Manage your login credentials and account security.
          </p>
        </div>

        {isLoading ? (
          <AccountSkeleton />
        ) : isError || !user ? (
          <div className="card-base rounded-xl p-8 text-center">
            <p className="text-sm text-text-secondary mb-4">Failed to load account details.</p>
            <Button variant="secondary" size="sm" onClick={() => refetch()}>Try again</Button>
          </div>
        ) : (
          <>
            {/* Email & verification */}
            <div className="card-base rounded-xl p-6">
              <h3 className="text-sm font-semibold text-text-primary mb-3">Email address</h3>
              <div className="flex items-center justify-between flex-wrap gap-3">
                <div className="flex items-center gap-2 text-sm text-text-secondary">
                  <Mail className="w-4 h-4 text-text-tertiary" aria-hidden="true" />
                  {user.email}
                </div>
                {user.email_verified ? (
                  <Badge variant="success" className="gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5" aria-hidden="true" />
                    Verified
                  </Badge>
                ) : (
                  <div className="flex items-center gap-3">
                    <Badge variant="warning" className="gap-1.5">
                      <MailWarning className="w-3.5 h-3.5" aria-hidden="true" />
                      Not verified
                    </Badge>
                    <Button variant="secondary" size="sm" loading={resending} onClick={handleResendVerification}>
                      Resend link
                    </Button>
                  </div>
                )}
              </div>
              <p className="text-xs text-text-tertiary mt-3">
                Account created {formatDate(user.created_at)}
              </p>
            </div>

            {/* Change password */}
            <form onSubmit={handleSubmit(onSubmit)} className="card-base rounded-xl p-6 space-y-5" noValidate>
              <div className="flex items-center gap-2">
                <KeyRound className="w-4 h-4 text-brand" aria-hidden="true" />
                <h3 className="text-sm font-semibold text-text-primary">Change password</h3>
              </div>

              <div>
                <Label htmlFor="currentPassword">Current password</Label>
                <div className="mt-1.5 max-w-sm">
                  <Input
                    id="currentPassword"
                    type="password"
                    autoComplete="current-password"
                    leftIcon={<Lock className="h-4 w-4" />}
                    error={errors.currentPassword?.message}
                    aria-invalid={!!errors.currentPassword}
                    {...register('currentPassword')}
                  />
                </div>
              </div>

              <Separator className="max-w-sm" />

              <div>
                <Label htmlFor="newPassword">New password</Label>
                <div className="mt-1.5 max-w-sm">
                  <Input
                    id="newPassword"
                    type="password"
                    autoComplete="new-password"
                    leftIcon={<Lock className="h-4 w-4" />}
                    error={errors.newPassword?.message}
                    aria-invalid={!!errors.newPassword}
                    aria-describedby="new-password-requirements"
                    {...register('newPassword')}
                  />
                </div>
                <div className="max-w-sm">
                  <PasswordRequirements password={newPasswordValue ?? ''} />
                </div>
              </div>

              <div>
                <Label htmlFor="confirmPassword">Confirm new password</Label>
                <div className="mt-1.5 max-w-sm">
                  <Input
                    id="confirmPassword"
                    type="password"
                    autoComplete="new-password"
                    leftIcon={<Lock className="h-4 w-4" />}
                    error={errors.confirmPassword?.message}
                    aria-invalid={!!errors.confirmPassword}
                    {...register('confirmPassword')}
                  />
                </div>
              </div>

              <p className="text-xs text-text-tertiary max-w-sm">
                Changing your password signs you out of every other device.
              </p>

              <div className="flex justify-end">
                <Button type="submit" loading={isSubmitting}>Update password</Button>
              </div>
            </form>
          </>
        )}
      </div>
    </SettingsLayout>
  )
}
