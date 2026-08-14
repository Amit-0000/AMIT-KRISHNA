import { useUIStore } from '@/store/uiStore'
import { useMediaQuery } from './useMediaQuery'

/**
 * Resolves the user's theme preference ('dark' | 'light' | 'system') down to
 * the actual 'dark' | 'light' currently in effect — the same computation
 * uiStore's applyTheme() does for the <html> class, exposed for the handful
 * of places (recharts SVG props, sonner's Toaster) that can't be themed via
 * CSS variables alone because they take literal color values as JS props.
 */
export function useResolvedTheme(): 'dark' | 'light' {
  const theme = useUIStore((s) => s.theme)
  const prefersDark = useMediaQuery('(prefers-color-scheme: dark)')
  if (theme === 'system') return prefersDark ? 'dark' : 'light'
  return theme
}
