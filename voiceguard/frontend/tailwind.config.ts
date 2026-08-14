import type { Config } from 'tailwindcss'
import animate from 'tailwindcss-animate'

const config: Config = {
  darkMode: ['class'],
  content: [
    './index.html',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Core backgrounds — CSS-variable-backed so they resolve differently
        // per theme (see index.css's `.dark`/`.light` blocks). The
        // `<alpha-value>` placeholder lets Tailwind's opacity modifiers
        // (e.g. `bg-bg-elevated/50`) keep working against the variable.
        bg: {
          base: 'rgb(var(--color-bg-base) / <alpha-value>)',
          surface: 'rgb(var(--color-bg-surface) / <alpha-value>)',
          elevated: 'rgb(var(--color-bg-elevated) / <alpha-value>)',
          overlay: 'rgb(var(--color-bg-overlay) / <alpha-value>)',
        },
        // Brand accent — intentionally theme-invariant (same purple reads
        // fine on both a near-black and a near-white surface).
        brand: {
          DEFAULT: '#7B6CEA',
          light: '#9B8FF5',
          dark: '#5A4DC8',
          muted: 'rgba(123, 108, 234, 0.15)',
          border: 'rgba(123, 108, 234, 0.3)',
        },
        // Verdict colors — also theme-invariant by design: these are status
        // colors (human/ai/uncertain) that must stay recognizable regardless
        // of theme, the same way a stop sign stays red in light or dark.
        human: {
          DEFAULT: '#32D583',
          muted: 'rgba(50, 213, 131, 0.12)',
          border: 'rgba(50, 213, 131, 0.25)',
          text: '#1FAD64',
        },
        ai: {
          DEFAULT: '#FF4F4F',
          muted: 'rgba(255, 79, 79, 0.12)',
          border: 'rgba(255, 79, 79, 0.25)',
          text: '#E03030',
        },
        uncertain: {
          DEFAULT: '#F5A623',
          muted: 'rgba(245, 166, 35, 0.12)',
          border: 'rgba(245, 166, 35, 0.25)',
          text: '#C8821A',
        },
        // Text hierarchy — CSS-variable-backed, swaps per theme.
        text: {
          primary: 'rgb(var(--color-text-primary) / <alpha-value>)',
          secondary: 'rgb(var(--color-text-secondary) / <alpha-value>)',
          tertiary: 'rgb(var(--color-text-tertiary) / <alpha-value>)',
          inverse: 'rgb(var(--color-text-inverse) / <alpha-value>)',
        },
        // Border system — derived from `chrome` below, at fixed alphas.
        border: {
          DEFAULT: 'rgb(var(--color-chrome) / 0.06)',
          subtle: 'rgb(var(--color-chrome) / 0.04)',
          strong: 'rgb(var(--color-chrome) / 0.12)',
        },
        // "Chrome" — the theme-relative neutral used for subtle borders,
        // hover overlays, and dividers throughout the app (previously
        // hardcoded as raw `white/N` utilities everywhere, which is why
        // light mode used to render identically to dark: white-on-white is
        // invisible). Resolves to white in dark mode, near-black in light
        // mode — same role `white/N` always played, now theme-aware.
        chrome: 'rgb(var(--color-chrome) / <alpha-value>)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      fontSize: {
        'display-xl': ['64px', { lineHeight: '1.05', letterSpacing: '-0.03em', fontWeight: '700' }],
        'display-lg': ['48px', { lineHeight: '1.1', letterSpacing: '-0.025em', fontWeight: '700' }],
        'display-md': ['36px', { lineHeight: '1.15', letterSpacing: '-0.02em', fontWeight: '600' }],
        'display-sm': ['28px', { lineHeight: '1.2', letterSpacing: '-0.015em', fontWeight: '600' }],
        'heading-xl': ['24px', { lineHeight: '1.3', letterSpacing: '-0.01em', fontWeight: '600' }],
        'heading-lg': ['20px', { lineHeight: '1.4', letterSpacing: '-0.005em', fontWeight: '600' }],
        'heading-md': ['18px', { lineHeight: '1.4', letterSpacing: '0', fontWeight: '600' }],
        'heading-sm': ['16px', { lineHeight: '1.5', letterSpacing: '0', fontWeight: '600' }],
        'body-lg': ['18px', { lineHeight: '1.6', letterSpacing: '0', fontWeight: '400' }],
        'body-md': ['16px', { lineHeight: '1.6', letterSpacing: '0', fontWeight: '400' }],
        'body-sm': ['14px', { lineHeight: '1.5', letterSpacing: '0', fontWeight: '400' }],
        'label-lg': ['14px', { lineHeight: '1', letterSpacing: '0.06em', fontWeight: '500' }],
        'label-md': ['12px', { lineHeight: '1', letterSpacing: '0.08em', fontWeight: '500' }],
      },
      spacing: {
        '18': '72px',
        '22': '88px',
        '26': '104px',
        '30': '120px',
      },
      borderRadius: {
        'sm': '6px',
        'md': '10px',
        'lg': '14px',
        'xl': '18px',
        '2xl': '24px',
        '3xl': '32px',
      },
      boxShadow: {
        'glow-brand': '0 0 40px rgba(123, 108, 234, 0.2)',
        'glow-human': '0 0 30px rgba(50, 213, 131, 0.25)',
        'glow-ai': '0 0 30px rgba(255, 79, 79, 0.25)',
        'card': '0 1px 3px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.05)',
        'card-hover': '0 4px 24px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(123, 108, 234, 0.2)',
        'elevated': '0 8px 32px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(255, 255, 255, 0.06)',
      },
      animation: {
        'fade-in': 'fadeIn 0.22s cubic-bezier(0.25, 0, 0, 1)',
        'slide-up': 'slideUp 0.35s cubic-bezier(0.25, 0, 0, 1)',
        'slide-down': 'slideDown 0.35s cubic-bezier(0.25, 0, 0, 1)',
        'scale-in': 'scaleIn 0.22s cubic-bezier(0.34, 1.56, 0.64, 1)',
        'pulse-brand': 'pulseBrand 2s ease-in-out infinite',
        'waveform': 'waveform 1.2s ease-in-out infinite',
        'gradient-shift': 'gradientShift 8s ease infinite',
        'float': 'float 6s ease-in-out infinite',
        'confidence-fill': 'confidenceFill 1.4s cubic-bezier(0.25, 0, 0, 1) forwards',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideDown: {
          '0%': { opacity: '0', transform: 'translateY(-16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        scaleIn: {
          '0%': { opacity: '0', transform: 'scale(0.92)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        pulseBrand: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.6' },
        },
        waveform: {
          '0%, 100%': { transform: 'scaleY(0.3)' },
          '50%': { transform: 'scaleY(1)' },
        },
        gradientShift: {
          '0%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
          '100%': { backgroundPosition: '0% 50%' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-8px)' },
        },
        confidenceFill: {
          '0%': { width: '0%' },
          '100%': { width: 'var(--target-width)' },
        },
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-brand': 'linear-gradient(135deg, #7B6CEA 0%, #9B8FF5 100%)',
        'gradient-hero': 'radial-gradient(ellipse 80% 50% at 50% -20%, rgba(123, 108, 234, 0.15) 0%, transparent 100%)',
        'gradient-surface': 'linear-gradient(180deg, #0E0E1A 0%, #080810 100%)',
        'noise': "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.03'/%3E%3C/svg%3E\")",
      },
      transitionTimingFunction: {
        'default': 'cubic-bezier(0.25, 0, 0, 1)',
        'spring': 'cubic-bezier(0.34, 1.56, 0.64, 1)',
        'decelerate': 'cubic-bezier(0, 0, 0.2, 1)',
        'accelerate': 'cubic-bezier(0.4, 0, 1, 1)',
      },
    },
  },
  plugins: [animate],
}

export default config
