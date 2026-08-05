import { Link, useLocation, useParams } from 'react-router-dom'
import { ChevronRight, Home } from 'lucide-react'
import { cn } from '@/lib/utils'
import { ROUTE_LABELS } from './nav-config'
import type { BreadcrumbItem } from '@/types'

const DYNAMIC_SEGMENT_LABELS: Record<string, string> = {
  scanId: 'Scan Result',
  articleSlug: 'Article',
}

function buildCrumbs(pathname: string, params: Readonly<Record<string, string | undefined>>): BreadcrumbItem[] {
  const crumbs: BreadcrumbItem[] = []

  // Always root the breadcrumb at Dashboard for authenticated routes
  if (pathname !== '/dashboard') {
    crumbs.push({ label: 'Dashboard', href: '/dashboard' })
  }

  const segments = pathname.split('/').filter(Boolean)
  let accumulated = ''

  for (let i = 0; i < segments.length; i++) {
    const seg = segments[i]
    accumulated += `/${seg}`

    const knownLabel = ROUTE_LABELS[accumulated]
    const isLast = i === segments.length - 1

    // Skip first segment if it's already shown as root
    if (accumulated === '/dashboard' && !isLast) continue

    const dynamicParamKey = Object.keys(params).find((key) => params[key] === seg)

    if (knownLabel) {
      crumbs.push({ label: knownLabel, href: isLast ? undefined : accumulated })
    } else if (dynamicParamKey && DYNAMIC_SEGMENT_LABELS[dynamicParamKey]) {
      crumbs.push({ label: DYNAMIC_SEGMENT_LABELS[dynamicParamKey], href: isLast ? undefined : accumulated })
    } else {
      // Dynamic segment with no friendly label — show an abbreviated ID
      const label = seg.length > 12 ? seg.slice(0, 8) + '…' : seg
      crumbs.push({ label, href: isLast ? undefined : accumulated })
    }
  }

  return crumbs
}

interface BreadcrumbProps {
  className?: string
  overrides?: BreadcrumbItem[]
}

export function Breadcrumb({ className, overrides }: BreadcrumbProps) {
  const location = useLocation()
  const params = useParams()
  const finalCrumbs = overrides ?? buildCrumbs(location.pathname, params)

  if (finalCrumbs.length === 0) return null

  return (
    <nav
      aria-label="Breadcrumb"
      className={cn('flex items-center gap-1 min-w-0', className)}
    >
      <ol className="flex items-center gap-1 min-w-0" role="list">
        {finalCrumbs.map((crumb, i) => {
          const isLast = i === finalCrumbs.length - 1
          const isFirst = i === 0

          return (
            <li key={i} className="flex items-center gap-1 min-w-0">
              {i > 0 && (
                <ChevronRight
                  className="w-3.5 h-3.5 text-text-tertiary flex-shrink-0"
                  aria-hidden="true"
                />
              )}
              {isFirst && !isLast && (
                <Home
                  className="w-3.5 h-3.5 text-text-tertiary mr-0.5 flex-shrink-0"
                  aria-hidden="true"
                />
              )}
              {isLast || !crumb.href ? (
                <span
                  className={cn(
                    'text-sm truncate',
                    isLast ? 'text-text-primary font-medium' : 'text-text-tertiary'
                  )}
                  aria-current={isLast ? 'page' : undefined}
                >
                  {crumb.label}
                </span>
              ) : (
                <Link
                  to={crumb.href}
                  className="text-sm text-text-tertiary hover:text-text-secondary transition-colors truncate focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand rounded"
                >
                  {crumb.label}
                </Link>
              )}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
