import { type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { Shield } from 'lucide-react'

interface AuthLayoutProps {
  title: string
  description?: string
  children: ReactNode
  footer?: ReactNode
}

export function AuthLayout({ title, description, children, footer }: AuthLayoutProps) {
  return (
    <div className="min-h-screen bg-bg-base bg-gradient-hero flex flex-col items-center justify-center px-4 py-12">
      <Link to="/" className="mb-8 flex items-center gap-2.5 group" aria-label="VoiceGuard home">
        <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-brand-muted border border-brand-border transition-colors group-hover:border-brand/50">
          <Shield className="w-5 h-5 text-brand" aria-hidden="true" />
        </div>
        <span className="text-heading-lg font-bold text-text-primary">VoiceGuard</span>
      </Link>

      <div className="w-full max-w-md bg-bg-elevated border border-white/8 rounded-2xl shadow-elevated p-8">
        <div className="mb-6 text-center">
          <h1 className="text-display-sm font-bold text-text-primary">{title}</h1>
          {description && <p className="mt-2 text-sm text-text-secondary">{description}</p>}
        </div>
        {children}
      </div>

      {footer && <div className="mt-6 text-sm text-text-secondary text-center">{footer}</div>}
    </div>
  )
}
