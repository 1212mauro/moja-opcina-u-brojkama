import { AccessibilityView, accessibilityMetadata } from "@/views/ProseViews";

export const metadata = accessibilityMetadata("en");

export default function Page() {
  return <AccessibilityView locale="en" />;
}
