import { Navbar } from '@/components/layout/Navbar'
import { Footer } from '@/components/layout/Footer'
import { HeroSection } from './sections/HeroSection'
import { SocialProofSection } from './sections/SocialProofSection'
import { HowItWorksSection } from './sections/HowItWorksSection'
import { VerdictShowcaseSection } from './sections/VerdictShowcaseSection'
import { TechnologySection } from './sections/TechnologySection'
import { ResponsibleAISection } from './sections/ResponsibleAISection'
import { UseCasesSection } from './sections/UseCasesSection'
import { CTASection } from './sections/CTASection'

export function LandingPage() {
  return (
    <div className="min-h-screen bg-bg-base noise-overlay">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-[100] focus:px-4 focus:py-2 focus:bg-brand focus:text-white focus:rounded-lg focus:text-sm focus:font-medium"
      >
        Skip to main content
      </a>

      <Navbar />

      <main id="main-content">
        <HeroSection />
        <SocialProofSection />
        <HowItWorksSection />
        <VerdictShowcaseSection />
        <TechnologySection />
        <ResponsibleAISection />
        <UseCasesSection />
        <CTASection />
      </main>

      <Footer />
    </div>
  )
}
