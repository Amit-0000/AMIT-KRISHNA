import { Link } from 'react-router-dom'
import { Shield, Github, Twitter } from 'lucide-react'

const FOOTER_LINKS = {
  Product: [
    { label: 'How it works', href: '#how-it-works' },
    { label: 'Technology', href: '#technology' },
    { label: 'Use cases', href: '#use-cases' },
    { label: 'Responsible AI', href: '#responsible-ai' },
  ],
  Account: [
    { label: 'Sign up free', href: '/signup' },
    { label: 'Sign in', href: '/login' },
  ],
  Legal: [
    // Terms of Service and Cookie Policy pages don't exist yet — no VoiceGuard
    // legal team has produced that copy, so this deliberately links only to
    // the one page that's real rather than pointing at 404s or placeholders.
    { label: 'Privacy & Data', href: '/help/data-privacy-and-retention' },
  ],
}

export function Footer() {
  return (
    <footer
      className="border-t border-chrome/6 bg-bg-surface pt-16 pb-10"
      role="contentinfo"
      aria-label="Site footer"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-12 mb-16">
          {/* Brand column */}
          <div className="lg:col-span-2">
            <Link
              to="/"
              className="inline-flex items-center gap-2.5 mb-5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand rounded-lg"
              aria-label="VoiceGuard homepage"
            >
              <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-brand-muted border border-brand-border">
                <Shield className="w-4 h-4 text-brand" aria-hidden="true" />
              </div>
              <span className="font-semibold text-base text-text-primary tracking-tight">
                Voice<span className="text-brand">Guard</span>
              </span>
            </Link>
            <p className="text-sm text-text-secondary leading-relaxed max-w-xs mb-6">
              Free, privacy-first audio deepfake detection. Powered by LCNN
              trained on ASVspoof 2019 LA dataset. Your audio is never stored
              permanently.
            </p>
            <div className="flex items-center gap-1.5 text-xs text-text-tertiary bg-human-muted border border-human-border rounded-full px-3 py-1.5 w-fit">
              <span
                className="w-1.5 h-1.5 rounded-full bg-human"
                aria-hidden="true"
              />
              Audio deleted within 60 seconds
            </div>
          </div>

          {/* Link columns */}
          {Object.entries(FOOTER_LINKS).map(([category, links]) => (
            <div key={category}>
              <h3 className="text-xs font-semibold text-text-tertiary uppercase tracking-widest mb-5">
                {category}
              </h3>
              <ul className="space-y-3" role="list">
                {links.map((link) => (
                  <li key={link.href}>
                    {link.href.startsWith('/') ? (
                      <Link
                        to={link.href}
                        className="text-sm text-text-secondary hover:text-text-primary transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand rounded"
                      >
                        {link.label}
                      </Link>
                    ) : (
                      <button
                        onClick={() => {
                          const el = document.querySelector(link.href)
                          el?.scrollIntoView({ behavior: 'smooth', block: 'start' })
                        }}
                        className="text-sm text-text-secondary hover:text-text-primary transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand rounded"
                      >
                        {link.label}
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom bar */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-8 border-t border-chrome/6">
          <p className="text-xs text-text-tertiary">
            © {new Date().getFullYear()} VoiceGuard. Free to use.
          </p>
          <div className="flex items-center gap-4">
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-text-tertiary hover:text-text-secondary transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand rounded"
              aria-label="VoiceGuard on GitHub"
            >
              <Github className="w-4 h-4" aria-hidden="true" />
            </a>
            <a
              href="https://twitter.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-text-tertiary hover:text-text-secondary transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand rounded"
              aria-label="VoiceGuard on X (Twitter)"
            >
              <Twitter className="w-4 h-4" aria-hidden="true" />
            </a>
          </div>
          <p className="text-xs text-text-tertiary">
            LCNN model · EER 7.07% · ASVspoof 2019 LA
          </p>
        </div>
      </div>
    </footer>
  )
}
