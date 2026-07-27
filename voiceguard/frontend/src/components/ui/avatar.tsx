import { cn } from '@/lib/utils'

interface AvatarProps {
  src?: string | null
  name?: string | null
  size?: 'xs' | 'sm' | 'md' | 'lg'
  className?: string
}

const SIZE_MAP = {
  xs: 'w-6 h-6 text-[10px]',
  sm: 'w-8 h-8 text-xs',
  md: 'w-9 h-9 text-sm',
  lg: 'w-12 h-12 text-base',
}

function getInitials(name: string | null | undefined): string {
  if (!name) return '?'
  const parts = name.trim().split(/\s+/)
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase()
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase()
}

function getColorFromName(name: string | null | undefined): string {
  const colors = [
    'bg-brand-muted text-brand',
    'bg-human-muted text-human',
    'bg-uncertain-muted text-uncertain',
    'bg-ai-muted text-ai',
  ]
  if (!name) return colors[0]
  const idx = name.charCodeAt(0) % colors.length
  return colors[idx]
}

export function Avatar({ src, name, size = 'md', className }: AvatarProps) {
  const sizeClass = SIZE_MAP[size]
  const colorClass = getColorFromName(name)
  const initials = getInitials(name)

  return (
    <div
      className={cn(
        'relative flex items-center justify-center rounded-full overflow-hidden flex-shrink-0 select-none font-semibold',
        sizeClass,
        !src && colorClass,
        className
      )}
      aria-hidden="true"
    >
      {src ? (
        <img
          src={src}
          alt=""
          className="w-full h-full object-cover"
          onError={(e) => {
            (e.currentTarget as HTMLImageElement).style.display = 'none'
          }}
        />
      ) : (
        <span>{initials}</span>
      )}
    </div>
  )
}
