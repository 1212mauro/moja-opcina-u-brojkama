import { MethodologyView, methodologyMetadata } from "@/views/ProseViews";

export const metadata = methodologyMetadata("en");

export default function Page() {
  return <MethodologyView locale="en" />;
}
