import { SourcesView, sourcesMetadata } from "@/views/SourcesView";

export const metadata = sourcesMetadata("hr");

export default function Page() {
  return <SourcesView locale="hr" />;
}
