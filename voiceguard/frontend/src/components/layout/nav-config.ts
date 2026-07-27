import type { LucideIcon } from 'lucide-react'
import {
  LayoutDashboard,
  Upload,
  Clock,
  Bell,
  HelpCircle,
  MessageSquare,
  Settings,
  User,
  Palette,
  KeyRound,
} from 'lucide-react'

export interface NavSection {
  id: string
  label?: string
  items: NavLinkItem[]
}

export interface NavLinkItem {
  id: string
  label: string
  href: string
  icon: LucideIcon
  matchExact?: boolean
  badge?: 'notification_count'
}

export const SIDEBAR_SECTIONS: NavSection[] = [
  {
    id: 'main',
    items: [
      {
        id: 'dashboard',
        label: 'Dashboard',
        href: '/dashboard',
        icon: LayoutDashboard,
        matchExact: true,
      },
      {
        id: 'new-scan',
        label: 'New Scan',
        href: '/scan/new',
        icon: Upload,
        matchExact: true,
      },
      {
        id: 'history',
        label: 'History',
        href: '/history',
        icon: Clock,
      },
      {
        id: 'notifications',
        label: 'Notifications',
        href: '/notifications',
        icon: Bell,
        badge: 'notification_count',
      },
    ],
  },
  {
    id: 'support',
    label: 'Support',
    items: [
      {
        id: 'help',
        label: 'Help Center',
        href: '/help',
        icon: HelpCircle,
      },
      {
        id: 'feedback',
        label: 'Give Feedback',
        href: '/feedback',
        icon: MessageSquare,
      },
    ],
  },
]

export const SETTINGS_ITEMS: NavLinkItem[] = [
  { id: 'profile', label: 'Profile', href: '/settings/profile', icon: User, matchExact: true },
  { id: 'account', label: 'Account', href: '/settings/account', icon: KeyRound, matchExact: true },
  { id: 'appearance', label: 'Appearance', href: '/settings/appearance', icon: Palette, matchExact: true },
]

export const SETTINGS_NAV: NavLinkItem = {
  id: 'settings',
  label: 'Settings',
  href: '/settings/profile',
  icon: Settings,
}

// Route → breadcrumb label mapping
export const ROUTE_LABELS: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/scan/new': 'New Scan',
  '/scan/processing': 'Processing',
  '/history': 'History',
  '/notifications': 'Notifications',
  '/help': 'Help Center',
  '/feedback': 'Feedback',
  '/settings': 'Settings',
  '/settings/profile': 'Profile',
  '/settings/account': 'Account',
  '/settings/appearance': 'Appearance',
  '/onboarding': 'Onboarding',
}
