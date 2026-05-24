import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Onboarding - VyOS Manager",
  description: "Setup your VyOS Manager instance",
};

export default function OnboardingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // No authentication check - onboarding must be accessible without auth
  return <>{children}</>;
}
