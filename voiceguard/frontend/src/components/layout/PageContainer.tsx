import { type ReactNode } from 'react'
import { cn } from '@/lib/utils'
import type { BreadcrumbItem } from '@/types'

interface PageContainerProps {
  children: ReactNode
  title?: string
  description?: string
  actions?: ReactNode
  breadcrumbs?: BreadcrumbItem[]
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'full'
  padding?: boolean
  className?: string
}

const MAX_WIDTH_MAP = {
  sm: 'max-w-2xl',
  md: 'max-w-4xl',
  lg: 'max-w-5xl',
  xl: 'max-w-6xl',
  '2xl': 'max-w-7xl',
  full: 'max-w-none',
}

export function PageContainer({
  children,
  title,
  description,
  actions,
  maxWidth = '2xl',
  padding = true,
  className,
}: PageContainerProps) {
  return (
    <div
      className={cn(
        'w-full mx-auto',
        MAX_WIDTH_MAP[maxWidth],
        padding && 'px-4 sm:px-6 lg:px-8 py-6',
        className
      )}
    >
      {(title || actions) && (
        <div className="flex items-start justify-between gap-4 mb-8">
          <div>
            {title && (
              <h1 className="text-display-sm font-bold text-text-primary">{title}</h1>
            )}
            {description && (
              <p className="mt-1 text-sm text-text-secondary">{description}</p>
            )}
          </div>
          {actions && (
            <div className="flex items-center gap-3 flex-shrink-0">{actions}</div>
          )}
        </div>
      )}
      {children}
    </div>
  )
}
