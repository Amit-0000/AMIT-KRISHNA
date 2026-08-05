import { Check, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { PASSWORD_REQUIREMENTS } from '@/lib/validation'

interface PasswordRequirementsProps {
  password: string
}

export function PasswordRequirements({ password }: PasswordRequirementsProps) {
  return (
    <ul className="mt-2 grid grid-cols-1 gap-1 sm:grid-cols-2" aria-label="Password requirements">
      {PASSWORD_REQUIREMENTS.map((req) => {
        const met = password.length > 0 && req.test(password)
        return (
          <li
            key={req.id}
            className={cn(
              'flex items-center gap-1.5 text-xs transition-colors',
              met ? 'text-human' : 'text-text-tertiary'
            )}
          >
            {met ? (
              <Check className="h-3 w-3 flex-shrink-0" aria-hidden="true" />
            ) : (
              <X className="h-3 w-3 flex-shrink-0" aria-hidden="true" />
            )}
            {req.label}
          </li>
        )
      })}
    </ul>
  )
}
