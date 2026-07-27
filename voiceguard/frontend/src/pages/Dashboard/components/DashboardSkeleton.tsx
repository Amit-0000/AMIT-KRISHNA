import React from 'react'
import { Skeleton } from '@/components/ui/skeleton'

function CardShell({ className = '', children }: { className?: string; children?: React.ReactNode }) {
  return (
    <div className={`card-base rounded-xl p-5 ${className}`} aria-hidden="true">
      {children}
    </div>
  )
}

export function DashboardSkeleton() {
  return (
    <div aria-label="Loading dashboard…" aria-busy="true">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-8">
        <div className="space-y-2">
          <Skeleton className="w-32 h-3.5 rounded" />
          <Skeleton className="w-64 h-8 rounded" />
          <Skeleton className="w-48 h-3.5 rounded" />
        </div>
        <Skeleton className="w-40 h-12 rounded-xl flex-shrink-0" />
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="card-base rounded-xl p-5">
            <div className="flex items-start justify-between mb-4">
              <Skeleton className="w-9 h-9 rounded-lg" />
              <Skeleton className="w-16 h-5 rounded-full" />
            </div>
            <Skeleton className="w-20 h-7 rounded mb-2" />
            <Skeleton className="w-28 h-3.5 rounded" />
          </div>
        ))}
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Left - 2 cols */}
        <div className="xl:col-span-2 space-y-6">
          {/* Trend chart */}
          <div className="card-base rounded-xl p-5">
            <div className="flex items-center justify-between mb-5">
              <div className="space-y-1.5">
                <Skeleton className="w-36 h-5 rounded" />
                <Skeleton className="w-48 h-3.5 rounded" />
              </div>
              <Skeleton className="w-32 h-8 rounded-lg" />
            </div>
            <Skeleton className="w-full h-[240px] rounded-lg" />
          </div>

          {/* Table */}
          <div className="card-base rounded-xl overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 border-b border-white/6">
              <Skeleton className="w-36 h-5 rounded" />
              <Skeleton className="w-64 h-9 rounded-lg" />
            </div>
            <div className="p-5 space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="flex gap-4">
                  <Skeleton className="w-8 h-8 rounded-lg flex-shrink-0" />
                  <Skeleton className="flex-1 h-8 rounded" />
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right sidebar - 1 col */}
        <div className="space-y-5">
          <CardShell>
            <Skeleton className="w-28 h-4 rounded mb-4" />
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-center gap-3 py-2">
                <Skeleton className="w-8 h-8 rounded-lg flex-shrink-0" />
                <Skeleton className="flex-1 h-3.5 rounded" />
              </div>
            ))}
          </CardShell>
          <CardShell>
            <Skeleton className="w-24 h-4 rounded mb-4" />
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex justify-between py-1.5">
                <Skeleton className="w-20 h-3.5 rounded" />
                <Skeleton className="w-16 h-3.5 rounded" />
              </div>
            ))}
          </CardShell>
          <div className="card-base rounded-xl p-4 space-y-3">
            <Skeleton className="w-full h-2 rounded-full" />
            <Skeleton className="w-1/2 h-3.5 rounded" />
          </div>
          <div className="card-base rounded-xl p-4 space-y-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="w-full h-3.5 rounded" />
            ))}
          </div>
        </div>
      </div>

      {/* Bottom charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        {Array.from({ length: 2 }).map((_, i) => (
          <div key={i} className="card-base rounded-xl p-5">
            <Skeleton className="w-48 h-5 rounded mb-1" />
            <Skeleton className="w-64 h-3.5 rounded mb-5" />
            <Skeleton className="w-full h-[200px] rounded-lg" />
          </div>
        ))}
      </div>
    </div>
  )
}
