import {
  MunicipalityView,
  municipalityMetadata,
  municipalityParams,
} from "@/views/MunicipalityView";

// Every municipality page is generated at build time; anything else is a 404.
export const dynamicParams = false;

export function generateStaticParams() {
  return municipalityParams();
}

export async function generateMetadata({
  params,
}: PageProps<"/jednostavno/opcina/[slug]">) {
  return municipalityMetadata("hr-simple", (await params).slug);
}

export default async function Page({
  params,
}: PageProps<"/jednostavno/opcina/[slug]">) {
  return <MunicipalityView locale="hr-simple" slug={(await params).slug} />;
}
