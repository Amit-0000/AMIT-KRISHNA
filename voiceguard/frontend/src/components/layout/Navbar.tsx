import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Menu, X, Shield, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { useScrollY } from '@/hooks/useScrollY'

const NAV_LINKS = [
  { label: 'How it works', href: '#how-it-works' },
  { label: 'Technology', href: '#technology' },
  { label: 'Use cases', href: '#use-cases' },
  { label: 'Responsible AI', href: '#responsible-ai' },
]

export function Navbar() {
  const scrollY = useScrollY()
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()
  const isLanding = location.pathname === '/'

  const scrolled = scrollY > 20

  const handleNavClick = (href: string) => {
    setMobileOpen(false)
    if (href.startsWith('#')) {
      const el = document.querySelector(href)
      el?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }

  return (
    <>
      <motion.header
        initial={{ y: -16, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.35, ease: [0.25, 0, 0, 1] }}
        className={cn(
          'fixed top-0 left-0 right-0 z-50 transition-all duration-300',
          scrolled
            ? 'surface-glass border-b border-chrome/6 py-3'
            : 'py-5 bg-transparent'
        )}
        role="banner"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav
            className="flex items-center justify-between"
            aria-label="Main navigation"
          >
            {/* Logo */}
            <Link
              to="/"
              className="flex items-center gap-2.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand rounded-lg"
              aria-label="VoiceGuard — Return to homepage"
            >
              <div className="relative flex items-center justify-center w-8 h-8 rounded-lg bg-brand-muted border border-brand-border">
                <Shield className="w-4 h-4 text-brand" aria-hidden="true" />
                <span
                  className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-human animate-pulse-brand"
                  aria-hidden="true"
                />
              </div>
              <span className="font-semibold text-base text-text-primary tracking-tight">
                Voice<span className="text-brand">Guard</span>
              </span>
            </Link>

            {/* Desktop nav links */}
            {isLanding && (
              <ul className="hidden md:flex items-center gap-6" role="list">
                {NAV_LINKS.map((link) => (
                  <li key={link.href}>
                    <button
                      onClick={() => handleNavClick(link.href)}
                      className="text-sm text-text-secondary hover:text-text-primary transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand rounded"
                    >
                      {link.label}
                    </button>
                  </li>
                ))}
              </ul>
            )}

            {/* Auth actions */}
            <div className="hidden md:flex items-center gap-3">
              <Link to="/login">
                <Button variant="ghost" size="sm">
                  Sign in
                </Button>
              </Link>
              <Link to="/signup">
                <Button size="sm" className="gap-1.5">
                  Get started free
                  <ChevronRight className="w-3.5 h-3.5" aria-hidden="true" />
                </Button>
              </Link>
            </div>

            {/* Mobile menu toggle */}
            <button
              className="md:hidden flex items-center justify-center w-9 h-9 rounded-lg text-text-secondary hover:text-text-primary hover:bg-chrome/5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
              onClick={() => setMobileOpen((v) => !v)}
              aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
              aria-expanded={mobileOpen}
              aria-controls="mobile-menu"
            >
              {mobileOpen ? (
                <X className="w-5 h-5" aria-hidden="true" />
              ) : (
                <Menu className="w-5 h-5" aria-hidden="true" />
              )}
            </button>
          </nav>
        </div>
      </motion.header>

      {/* Mobile menu */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            id="mobile-menu"
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.22, ease: [0.25, 0, 0, 1] }}
            className="fixed inset-x-0 top-[60px] z-40 surface-glass border-b border-chrome/6 px-4 py-6 md:hidden"
            role="dialog"
            aria-label="Mobile navigation"
          >
            {isLanding && (
              <ul className="flex flex-col gap-1 mb-6" role="list">
                {NAV_LINKS.map((link) => (
                  <li key={link.href}>
                    <button
                      onClick={() => handleNavClick(link.href)}
                      className="w-full text-left px-4 py-3 text-sm text-text-secondary hover:text-text-primary hover:bg-chrome/5 rounded-lg transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
                    >
                      {link.label}
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <div className="flex flex-col gap-3">
              <Link to="/login" onClick={() => setMobileOpen(false)}>
                <Button variant="secondary" className="w-full">
                  Sign in
                </Button>
              </Link>
              <Link to="/signup" onClick={() => setMobileOpen(false)}>
                <Button className="w-full gap-1.5">
                  Get started free
                  <ChevronRight className="w-3.5 h-3.5" aria-hidden="true" />
                </Button>
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
