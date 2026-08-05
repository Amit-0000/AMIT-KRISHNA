import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Mail, Lock, User, MailCheck } from 'lucide-react'
import { toast } from 'sonner'
import { AuthLayout } from '@/components/layout/AuthLayout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { authApi } from '@/services/api'
import { parseApiError } from '@/lib/apiError'
import { emailSchema, passwordSchema, displayNameSchema } from '@/lib/validation'
import { PasswordRequirements } from './components/PasswordRequirements'

const signupSchema = z
  .object({
    displayName: displayNameSchema,
    email: emailSchema,
    password: passwordSchema,
    confirmPassword: z.string().min(1, 'Please confirm your password'),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  })

type SignupFormValues = z.infer<typeof signupSchema>

const SERVER_FIELD_MAP: Record<string, keyof SignupFormValues> = {
  email: 'email',
  password: 'password',
  display_name: 'displayName',
}

export function SignupPage() {
  const [submittedEmail, setSubmittedEmail] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    setError,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<SignupFormValues>({
    resolver: zodResolver(signupSchema),
    mode: 'onBlur',
    defaultValues: { displayName: '', email: '', password: '', confirmPassword: '' },
  })

  const passwordValue = watch('password')

  async function onSubmit(values: SignupFormValues) {
    try {
      await authApi.signup(values.email, values.password, values.displayName)
      setSubmittedEmail(values.email)
    } catch (err) {
      const parsed = parseApiError(err)

      if (parsed.code === 'EMAIL_ALREADY_EXISTS') {
        setError('email', { type: 'server', message: 'An account with this email already exists.' })
        return
      }

      if (parsed.details.length > 0) {
        for (const detail of parsed.details) {
          const field = detail.field ? SERVER_FIELD_MAP[detail.field] : undefined
          if (field) setError(field, { type: 'server', message: detail.message })
        }
        return
      }

      toast.error(parsed.message)
    }
  }

  if (submittedEmail) {
    return (
      <AuthLayout title="Check your email">
        <div className="flex flex-col items-center text-center gap-4">
          <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-brand-muted border border-brand-border">
            <MailCheck className="w-7 h-7 text-brand" aria-hidden="true" />
          </div>
          <p className="text-sm text-text-secondary">
            We sent a verification link to <span className="text-text-primary font-medium">{submittedEmail}</span>.
            Click the link to activate your account, then sign in.
          </p>
          <Button asChild variant="secondary" className="w-full">
            <Link to="/login">Go to login</Link>
          </Button>
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout
      title="Create your account"
      description="Detect AI-generated speech with forensic-grade accuracy."
      footer={
        <>
          Already have an account?{' '}
          <Link to="/login" className="text-brand hover:text-brand-light font-medium">
            Log in
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
        <div>
          <Label htmlFor="displayName">Display name</Label>
          <div className="mt-1.5">
            <Input
              id="displayName"
              type="text"
              autoComplete="name"
              autoFocus
              leftIcon={<User className="h-4 w-4" />}
              aria-invalid={!!errors.displayName}
              aria-describedby={errors.displayName ? 'displayName-error' : undefined}
              error={errors.displayName?.message}
              {...register('displayName')}
            />
          </div>
        </div>

        <div>
          <Label htmlFor="email">Email</Label>
          <div className="mt-1.5">
            <Input
              id="email"
              type="email"
              autoComplete="email"
              leftIcon={<Mail className="h-4 w-4" />}
              aria-invalid={!!errors.email}
              aria-describedby={errors.email ? 'email-error' : undefined}
              error={errors.email?.message}
              {...register('email')}
            />
          </div>
        </div>

        <div>
          <Label htmlFor="password">Password</Label>
          <div className="mt-1.5">
            <Input
              id="password"
              type="password"
              autoComplete="new-password"
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
          <Label htmlFor="confirmPassword">Confirm password</Label>
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
          Create account
        </Button>

        <p className="text-xs text-text-tertiary text-center">
          By signing up, you agree to VoiceGuard's Terms of Service and Privacy Policy.
        </p>
      </form>
    </AuthLayout>
  )
}
