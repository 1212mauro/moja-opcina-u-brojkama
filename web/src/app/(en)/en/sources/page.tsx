import { SourcesView, sourcesMetadata } from "@/views/SourcesView";

export const metadata = sourcesMetadata("en");

export default function Page() {
  return <SourcesView locale="en" />;
}
