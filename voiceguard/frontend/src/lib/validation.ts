import { z } from 'zod'

export const emailSchema = z
  .string()
  .trim()
  .min(1, 'Email is required')
  .max(254, 'Email is too long')
  .email('Enter a valid email address')

export interface PasswordRequirement {
  id: string
  label: string
  test: (value: string) => boolean
}

export const PASSWORD_REQUIREMENTS: PasswordRequirement[] = [
  { id: 'length', label: 'At least 8 characters', test: (v) => v.length >= 8 },
  { id: 'upper', label: 'One uppercase letter', test: (v) => /[A-Z]/.test(v) },
  { id: 'lower', label: 'One lowercase letter', test: (v) => /[a-z]/.test(v) },
  { id: 'digit', label: 'One number', test: (v) => /[0-9]/.test(v) },
  {
    id: 'special',
    label: 'One special character',
    test: (v) => /[!@#$%^&*()_+\-=[\]{}|;:,.<>?]/.test(v),
  },
]

export const passwordSchema = z
  .string()
  .min(1, 'Password is required')
  .refine(
    (v) => PASSWORD_REQUIREMENTS.every((req) => req.test(v)),
    'Password does not meet the requirements below'
  )

export const displayNameSchema = z
  .string()
  .trim()
  .min(1, 'Display name is required')
  .max(64, 'Display name must be 64 characters or fewer')
  .regex(/^[a-zA-Z0-9 .'_-]+$/, "Use only letters, numbers, spaces, and . ' - _")
