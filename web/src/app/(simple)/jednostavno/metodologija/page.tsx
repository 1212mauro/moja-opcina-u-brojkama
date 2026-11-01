import { MethodologyView, methodologyMetadata } from "@/views/ProseViews";

export const metadata = methodologyMetadata("hr-simple");

export default function Page() {
  return <MethodologyView locale="hr-simple" />;
}
