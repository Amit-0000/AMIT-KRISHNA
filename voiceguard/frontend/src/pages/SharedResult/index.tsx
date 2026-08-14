import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ChevronRight, LinkIcon, ShieldOff } from 'lucide-react'
import { Navbar } from '@/components/layout/Navbar'
import { Footer } from '@/components/layout/Footer'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { scanApi } from '@/services/api'
import { formatDate } from '@/lib/utils'
import { VerdictCard } from '@/pages/ScanResult/components/VerdictCard'

export function SharedResultPage() {
  const { scanId } = useParams<{ scanId: string }>()

  const query = useQuery({
    queryKey: ['shared-result', scanId],
    queryFn: async () => {
      const { data } = await scanApi.sharedResult(scanId!)
      return data.result
    },
    enabled: !!scanId,
    retry: false,
  })

  return (
    <div className="min-h-screen bg-bg-base noise-overlay flex flex-col">
      <Navbar />

      <main id="main-content" className="flex-1 pt-28 pb-20 px-4">
        <div className="max-w-md mx-auto">
          {query.isLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-56 rounded-2xl" />
              <Skeleton className="h-10 rounded-lg" />
            </div>
          ) : query.isError || !query.data ? (
            <div className="card-base rounded-2xl p-8 text-center">
              <div className="w-14 h-14 rounded-2xl bg-chrome/5 border border-chrome/8 flex items-center justify-center mx-auto mb-5">
                <ShieldOff className="w-6 h-6 text-text-tertiary" aria-hidden="true" />
              </div>
              <h1 className="text-heading-lg font-semibold text-text-primary mb-2">
                This shared result isn't available
              </h1>
              <p className="text-sm text-text-secondary mb-6">
                The link may be invalid, expired, or the person who shared it may no longer be sharing it.
                Public sharing is still rolling out — if you were sent this link recently, ask the sender
                to try generating it again.
              </p>
              <Link to="/">
                <Button variant="secondary" className="gap-2">
                  Go to VoiceGuard
                  <ChevronRight className="w-4 h-4" aria-hidden="true" />
                </Button>
              </Link>
            </div>
          ) : (
            <div className="space-y-5">
              <div className="flex items-center justify-center gap-2 text-xs text-text-tertiary">
                <LinkIcon className="w-3.5 h-3.5" aria-hidden="true" />
                Publicly shared result
              </div>

              <VerdictCard verdict={query.data.verdict} confidence={query.data.confidence} />

              <p className="text-center text-xs text-text-tertiary">
                Analyzed {formatDate(query.data.created_at)} · Model {query.data.model_version}
              </p>

              <div className="card-base rounded-xl p-5 text-center">
                <p className="text-sm text-text-secondary mb-3">
                  Want to check your own audio for AI-generated speech?
                </p>
                <Link to="/signup">
                  <Button className="gap-1.5">
                    Try VoiceGuard free
                    <ChevronRight className="w-3.5 h-3.5" aria-hidden="true" />
                  </Button>
                </Link>
              </div>
            </div>
          )}
        </div>
      </main>

      <Footer />
    </div>
  )
}
