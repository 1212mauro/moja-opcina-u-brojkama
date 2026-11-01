import type { Metadata } from "next";

import { SiteLayout } from "@/components/SiteLayout";
import { hr } from "@/messages/hr";
import { NotFoundView } from "@/views/ProseViews";
import "./globals.css";

// Several root layouts (one per edition), so the 404 page brings its own (F2).
export const metadata: Metadata = {
  title: `${hr.notFound.title} · ${hr.site.name}`,
};

export default function GlobalNotFound() {
  return (
    <SiteLayout locale="hr">
      <NotFoundView />
    </SiteLayout>
  );
}
