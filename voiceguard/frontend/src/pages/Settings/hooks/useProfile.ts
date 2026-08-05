import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { userApi } from '@/services/api'
import { useAuthStore } from '@/store/authStore'

const QUERY_KEY = 'user-profile'

export function useProfile() {
  const setUser = useAuthStore((s) => s.setUser)

  const query = useQuery({
    queryKey: [QUERY_KEY],
    queryFn: async () => {
      const { data } = await userApi.profile()
      return data.user
    },
    staleTime: 60_000,
  })

  return {
    user: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    refetch: query.refetch,
    setUser,
  }
}

export function useUpdateProfile() {
  const qc = useQueryClient()
  const setUser = useAuthStore((s) => s.setUser)

  return useMutation({
    mutationFn: (display_name: string) => userApi.updateProfile(display_name),
    onSuccess: ({ data }) => {
      setUser(data.user)
      qc.setQueryData([QUERY_KEY], data.user)
    },
  })
}

export function useChangePassword() {
  return useMutation({
    mutationFn: ({ currentPassword, newPassword }: { currentPassword: string; newPassword: string }) =>
      userApi.changePassword(currentPassword, newPassword),
  })
}
