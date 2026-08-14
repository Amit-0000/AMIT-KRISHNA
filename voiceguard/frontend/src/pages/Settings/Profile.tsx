import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'
import { AlertTriangle, Mail, RefreshCw, ShieldCheck } from 'lucide-react'
import { SettingsLayout } from './SettingsLayout'
import { Avatar } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { Separator } from '@/components/ui/separator'
import { displayNameSchema } from '@/lib/validation'
import { parseApiError } from '@/lib/apiError'
import { formatDate } from '@/lib/utils'
import { useProfile, useUpdateProfile } from './hooks/useProfile'
import { z } from 'zod'

const profileSchema = z.object({ displayName: displayNameSchema })
type ProfileFormValues = z.infer<typeof profileSchema>

function ProfileSkeleton() {
  return (
    <div className="card-base rounded-xl p-6 space-y-5">
      <div className="flex items-center gap-4">
        <Skeleton className="w-16 h-16 rounded-full" />
        <div className="space-y-2 flex-1">
          <Skeleton className="h-4 w-40 rounded" />
          <Skeleton className="h-3 w-56 rounded" />
        </div>
      </div>
      <Skeleton className="h-10 rounded-lg" />
      <Skeleton className="h-10 rounded-lg" />
    </div>
  )
}

function ProfileErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="card-base rounded-xl p-8 text-center">
      <div className="w-12 h-12 rounded-2xl bg-ai-muted border border-ai-border flex items-center justify-center mx-auto mb-4">
        <AlertTriangle className="w-6 h-6 text-ai" aria-hidden="true" />
      </div>
      <p className="text-sm text-text-secondary mb-4">Failed to load your profile.</p>
      <Button variant="secondary" size="sm" onClick={onRetry} className="gap-2">
        <RefreshCw className="w-3.5 h-3.5" aria-hidden="true" />
        Try again
      </Button>
    </div>
  )
}

export function ProfilePage() {
  const { user, isLoading, isError, refetch } = useProfile()
  const updateProfile = useUpdateProfile()

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isDirty },
  } = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: { displayName: '' },
  })

  useEffect(() => {
    if (user) reset({ displayName: user.display_name })
  }, [user, reset])

  async function onSubmit(values: ProfileFormValues) {
    try {
      await updateProfile.mutateAsync(values.displayName)
      toast.success('Profile updated')
      reset({ displayName: values.displayName })
    } catch (err) {
      toast.error(parseApiError(err).message)
    }
  }

  return (
    <SettingsLayout>
      <div className="space-y-6">
        <div>
          <h2 className="text-heading-lg font-semibold text-text-primary">Profile</h2>
          <p className="text-sm text-text-secondary mt-1">
            This information is visible on your account and used to personalize VoiceGuard.
          </p>
        </div>

        {isLoading ? (
          <ProfileSkeleton />
        ) : isError || !user ? (
          <ProfileErrorState onRetry={() => refetch()} />
        ) : (
          <form onSubmit={handleSubmit(onSubmit)} className="card-base rounded-xl p-6 space-y-6" noValidate>
            <div className="flex items-center gap-4">
              <Avatar src={user.avatar_url} name={user.display_name} size="lg" />
              <div>
                <p className="text-sm font-medium text-text-primary">{user.display_name}</p>
                <div className="flex items-center gap-1.5 mt-1 text-xs text-text-tertiary">
                  <Mail className="w-3.5 h-3.5" aria-hidden="true" />
                  {user.email}
                  {user.email_verified && (
                    <Badge variant="success" className="ml-1 py-0 px-1.5 gap-1 text-[10px]">
                      <ShieldCheck className="w-3 h-3" aria-hidden="true" />
                      Verified
                    </Badge>
                  )}
                </div>
              </div>
            </div>

            <Separator />

            <div>
              <Label htmlFor="displayName">Display name</Label>
              <div className="mt-1.5 max-w-sm">
                <Input
                  id="displayName"
                  autoComplete="name"
                  error={errors.displayName?.message}
                  aria-invalid={!!errors.displayName}
                  {...register('displayName')}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 max-w-sm text-sm">
              <div>
                <p className="text-xs text-text-tertiary uppercase tracking-wider mb-1">Plan</p>
                <Badge variant="default" className="capitalize">{user.subscription_tier}</Badge>
              </div>
              <div>
                <p className="text-xs text-text-tertiary uppercase tracking-wider mb-1">Member since</p>
                <p className="text-text-secondary">{formatDate(user.created_at)}</p>
              </div>
            </div>

            <div>
              <p className="text-xs text-text-tertiary uppercase tracking-wider mb-1.5">Daily scan usage</p>
              <div className="flex items-center gap-3 max-w-sm">
                <div className="flex-1 h-2 rounded-full bg-chrome/5 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-brand"
                    style={{
                      width: `${Math.min(100, Math.round((user.scan_count_today / Math.max(user.scan_limit_daily, 1)) * 100))}%`,
                    }}
                  />
                </div>
                <span className="text-xs text-text-tertiary tabular-nums whitespace-nowrap">
                  {user.scan_count_today} / {user.scan_limit_daily} today
                </span>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <Button type="submit" disabled={!isDirty} loading={updateProfile.isPending}>
                Save changes
              </Button>
            </div>
          </form>
        )}
      </div>
    </SettingsLayout>
  )
}
