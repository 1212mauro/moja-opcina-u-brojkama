import { AccessibilityView, accessibilityMetadata } from "@/views/ProseViews";

export const metadata = accessibilityMetadata("hr-simple");

export default function Page() {
  return <AccessibilityView locale="hr-simple" />;
}
