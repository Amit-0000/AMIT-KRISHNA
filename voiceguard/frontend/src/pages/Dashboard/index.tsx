import { useAuthStore } from '@/store/authStore'
import { PageContainer } from '@/components/layout/PageContainer'
import { useDashboardData } from './hooks/useDashboardData'
import { DashboardHeader } from './components/DashboardHeader'
import { StatsGrid } from './components/StatsGrid'
import { TrendChart } from './components/TrendChart'
import { ConfidenceChart } from './components/ConfidenceChart'
import { RecentAnalysisTable } from './components/RecentAnalysisTable'
import { ActivityFeed } from './components/ActivityFeed'
import { QuickActions } from './components/QuickActions'
import { ModelStatusCard } from './components/ModelStatusCard'
import { StorageCard } from './components/StorageCard'
import { PrivacyCard } from './components/PrivacyCard'
import { EmptyDashboard } from './components/EmptyDashboard'
import { DashboardSkeleton } from './components/DashboardSkeleton'
import { DashboardErrorState } from './components/DashboardErrorState'

export function DashboardPage() {
  const user = useAuthStore((s) => s.user)
  const { data, isLoading, isError, refetch } = useDashboardData()

  if (isLoading) {
    return (
      <PageContainer maxWidth="2xl">
        <DashboardSkeleton />
      </PageContainer>
    )
  }

  if (isError) {
    return (
      <PageContainer maxWidth="2xl">
        <DashboardErrorState onRetry={refetch} />
      </PageContainer>
    )
  }

  const isEmpty = data?.stats.total_scans === 0

  return (
    <PageContainer maxWidth="2xl">
      {/* Welcome header */}
      <DashboardHeader
        user={user}
        scansToday={data?.stats.scans_today ?? 0}
        dailyLimit={data?.stats.scan_limit_daily ?? 50}
      />

      {isEmpty ? (
        <EmptyDashboard />
      ) : (
        <>
          {/* Stats */}
          <StatsGrid stats={data?.stats} loading={false} />

          {/* Main 2/3 + 1/3 grid */}
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
            {/* Left — main content */}
            <div className="xl:col-span-2 space-y-6">
              <TrendChart data={data?.trend} loading={false} />
              <RecentAnalysisTable />
            </div>

            {/* Right — sidebar */}
            <div className="space-y-5">
              <QuickActions />
              <ModelStatusCard status={data?.model_status} loading={false} />
              <StorageCard stats={data?.stats} loading={false} />
              <PrivacyCard />
            </div>
          </div>

          {/* Bottom row — confidence chart + activity feed */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
            <ConfidenceChart data={data?.confidence_distribution} loading={false} />
            <ActivityFeed items={data?.recent_activity} loading={false} />
          </div>
        </>
      )}
    </PageContainer>
  )
}
