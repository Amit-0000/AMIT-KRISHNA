import { useNavigate } from 'react-router-dom'
import {
  User,
  Settings,
  LogOut,
  ChevronDown,
  CreditCard,
  Palette,
} from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuGroup,
} from '@/components/ui/dropdown-menu'
import { Avatar } from '@/components/ui/avatar'
import { useAuth } from '@/hooks/useAuth'
import { cn } from '@/lib/utils'

interface UserMenuProps {
  collapsed?: boolean
}

export function UserMenu({ collapsed = false }: UserMenuProps) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/', { replace: true })
  }

  if (!user) return null

  const initials = user.display_name

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          className={cn(
            'flex items-center gap-2.5 rounded-lg px-2 py-1.5 transition-colors',
            'hover:bg-chrome/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand',
            collapsed ? 'justify-center w-10 h-10 p-0' : 'w-full'
          )}
          aria-label={collapsed ? `Account menu for ${user.display_name}` : undefined}
        >
          <Avatar src={user.avatar_url} name={initials} size="sm" />
          {!collapsed && (
            <>
              <div className="flex-1 min-w-0 text-left">
                <p className="text-sm font-medium text-text-primary truncate leading-tight">
                  {user.display_name}
                </p>
                <p className="text-xs text-text-tertiary truncate leading-tight">
                  {user.email}
                </p>
              </div>
              <ChevronDown className="w-3.5 h-3.5 text-text-tertiary flex-shrink-0" aria-hidden="true" />
            </>
          )}
        </button>
      </DropdownMenuTrigger>

      <DropdownMenuContent
        align={collapsed ? 'end' : 'end'}
        side={collapsed ? 'right' : 'top'}
        className="w-56"
      >
        {/* User identity */}
        <div className="px-2.5 py-2.5 border-b border-chrome/8 mb-1">
          <p className="text-sm font-medium text-text-primary truncate">{user.display_name}</p>
          <p className="text-xs text-text-tertiary truncate mt-0.5">{user.email}</p>
          <span className="inline-block mt-2 text-[10px] font-semibold uppercase tracking-widest px-2 py-0.5 rounded-full bg-brand-muted border border-brand-border text-brand">
            {user.subscription_tier}
          </span>
        </div>

        <DropdownMenuGroup>
          <DropdownMenuLabel>Account</DropdownMenuLabel>
          <DropdownMenuItem onClick={() => navigate('/settings/profile')}>
            <User className="w-4 h-4" aria-hidden="true" />
            Profile
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => navigate('/settings/account')}>
            <CreditCard className="w-4 h-4" aria-hidden="true" />
            Account settings
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => navigate('/settings/appearance')}>
            <Palette className="w-4 h-4" aria-hidden="true" />
            Appearance
          </DropdownMenuItem>
        </DropdownMenuGroup>

        <DropdownMenuSeparator />

        <DropdownMenuGroup>
          <DropdownMenuItem onClick={() => navigate('/settings/profile')}>
            <Settings className="w-4 h-4" aria-hidden="true" />
            Settings
          </DropdownMenuItem>
          <DropdownMenuItem destructive onClick={handleLogout}>
            <LogOut className="w-4 h-4" aria-hidden="true" />
            Sign out
          </DropdownMenuItem>
        </DropdownMenuGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
