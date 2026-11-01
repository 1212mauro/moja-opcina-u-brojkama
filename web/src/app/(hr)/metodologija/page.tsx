import { MethodologyView, methodologyMetadata } from "@/views/ProseViews";

export const metadata = methodologyMetadata("hr");

export default function Page() {
  return <MethodologyView locale="hr" />;
}
