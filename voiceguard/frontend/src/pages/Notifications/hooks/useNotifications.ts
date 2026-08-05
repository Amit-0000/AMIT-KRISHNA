import { useEffect, useState } from 'react'
import { notificationApi } from '@/services/api'
import { useUIStore } from '@/store/uiStore'

export function useNotifications() {
  const notifications = useUIStore((s) => s.notifications)
  const setNotifications = useUIStore((s) => s.setNotifications)
  const markRead = useUIStore((s) => s.markNotificationRead)
  const markAllRead = useUIStore((s) => s.markAllNotificationsRead)
  const unreadCount = useUIStore((s) => s.unreadCount)

  const [isLoading, setIsLoading] = useState(notifications.length === 0)
  const [isError, setIsError] = useState(false)

  function load() {
    setIsLoading(true)
    setIsError(false)
    notificationApi
      .list()
      .then(({ data }) => setNotifications(data))
      .catch(() => setIsError(true))
      .finally(() => setIsLoading(false))
  }

  useEffect(() => {
    if (notifications.length > 0) {
      setIsLoading(false)
      return
    }
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleMarkRead(id: string) {
    markRead(id)
    try {
      await notificationApi.markRead(id)
    } catch {
      /* best-effort */
    }
  }

  async function handleMarkAllRead() {
    markAllRead()
    try {
      await notificationApi.markAllRead()
    } catch {
      /* best-effort */
    }
  }

  return {
    notifications,
    unreadCount,
    isLoading,
    isError,
    refetch: load,
    markRead: handleMarkRead,
    markAllRead: handleMarkAllRead,
  }
}
