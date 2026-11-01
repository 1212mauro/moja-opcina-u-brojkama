import type { ReactNode } from "react";

import { SiteLayout, siteMetadata } from "@/components/SiteLayout";
import "../globals.css";

export const metadata = siteMetadata("en");

export default function Layout({ children }: { children: ReactNode }) {
  return <SiteLayout locale="en">{children}</SiteLayout>;
}
