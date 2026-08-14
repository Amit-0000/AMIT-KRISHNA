import { Skeleton } from '@/components/ui/skeleton'

export function UploadSkeleton() {
  return (
    <div aria-label="Loading upload interface…" aria-busy="true" className="space-y-5">
      {/* Dropzone placeholder */}
      <div className="rounded-2xl border-2 border-dashed border-chrome/8 min-h-[340px] flex flex-col items-center justify-center gap-5 p-8">
        <Skeleton className="w-20 h-20 rounded-2xl" />
        <div className="space-y-2.5 text-center">
          <Skeleton className="w-52 h-5 rounded mx-auto" />
          <Skeleton className="w-36 h-4 rounded mx-auto" />
          <Skeleton className="w-64 h-3.5 rounded mx-auto" />
        </div>
      </div>

      {/* Privacy notice placeholder */}
      <div className="rounded-xl border border-chrome/6 bg-chrome/[0.02] px-4 py-3.5">
        <div className="flex gap-3">
          <Skeleton className="w-7 h-7 rounded-lg flex-shrink-0" />
          <div className="flex-1 space-y-2">
            <Skeleton className="w-28 h-3.5 rounded" />
            <Skeleton className="w-full h-3 rounded" />
            <Skeleton className="w-4/5 h-3 rounded" />
            <Skeleton className="w-5/6 h-3 rounded" />
          </div>
        </div>
      </div>
    </div>
  )
}
