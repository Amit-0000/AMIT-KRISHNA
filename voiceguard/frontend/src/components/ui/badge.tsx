import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors',
  {
    variants: {
      variant: {
        default: 'bg-brand-muted text-brand border border-brand-border',
        human: 'bg-human-muted text-human border border-human-border',
        ai: 'bg-ai-muted text-ai border border-ai-border',
        uncertain: 'bg-uncertain-muted text-uncertain border border-uncertain-border',
        neutral: 'bg-chrome/8 text-text-secondary border border-chrome/10',
        success: 'bg-human-muted text-human border border-human-border',
        warning: 'bg-uncertain-muted text-uncertain border border-uncertain-border',
        error: 'bg-ai-muted text-ai border border-ai-border',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
