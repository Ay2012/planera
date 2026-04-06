import { CTASection } from "@/components/marketing/CTASection";
import { FeatureGrid } from "@/components/marketing/FeatureGrid";
import { HeroSection } from "@/components/marketing/HeroSection";
import { HowItWorks } from "@/components/marketing/HowItWorks";
import { PricingSection } from "@/components/marketing/PricingSection";
import { TrustStrip } from "@/components/marketing/TrustStrip";
import { UseCases } from "@/components/marketing/UseCases";
import { MarketingLayout } from "@/layouts/MarketingLayout";

export function HomePage() {
  return (
    <MarketingLayout>
      <HeroSection />
      <TrustStrip />
      <HowItWorks />
      <FeatureGrid />
      <UseCases />
      <PricingSection />
      <CTASection />
    </MarketingLayout>
  );
}
